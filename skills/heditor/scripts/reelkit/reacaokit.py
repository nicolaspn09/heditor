"""Helpers for the style `reacao` (the speaker reacting in front of the post/news): backdrops and the speaker cutout.

A backdrop is the subject the speaker reacts to, drawn full-bleed behind the cutout:
- an image (screenshot, full-page capture of an article, a post exported by the user), static or scrolled;
- a region of the raw recording itself (`region_clip`): split-screen exports, screen shares, a phone filming a
  monitor. The region is cut with the same EDL as camera-src.mp4, so the backdrop stays frame for frame in sync;
- an external clip (a screen recording of the post, a launch video), played from a media offset.

CLI:
    heditor capture <url> <out.png> [--desktop] [--dark] [--viewport] [--width 430] [--height 932] [--scale 2]
                    [--wait 2.5] [--selector CSS] [--hide CSS,CSS] [--max-height 14000]
    heditor region <work> <name> <crop=w:h:x:y> [extra ffmpeg filters]
Login walls (X, Instagram, LinkedIn) usually block captures: ask the user for a screenshot or a screen recording.
"""
import json
import subprocess
import sys
from pathlib import Path

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Version/18.0 Mobile/15E148 Safari/604.1")


def run(cmd, timeout=3600):
    subprocess.run([str(c) for c in cmd], check=True, timeout=timeout)


def probe(path):
    """(width, height, duration_s or None) of an image or a video."""
    path = Path(path)
    if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        from PIL import Image
        with Image.open(path) as im:
            return im.size[0], im.size[1], None
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    return int(s["width"]), int(s["height"]), float(d["format"].get("duration") or 0) or None


def stale(out, *srcs):
    out = Path(out)
    if not out.exists():
        return True
    return any(Path(s).exists() and Path(s).stat().st_mtime > out.stat().st_mtime for s in srcs)


def _even(v):
    v = int(round(float(v)))
    return v - v % 2


def _parse_crop(crop):
    w, h, x, y = (int(float(v)) for v in crop.split("=", 1)[1].split(":"))
    return _even(w), _even(h), x, y


# ------------------------------------------------------------------ backdrops from the raw recording
def region_clip(work, name, crop, vf="", source=None, crf=16):
    """Cut `crop` (\"crop=w:h:x:y\") of the source with the EDL of camera-src.mp4 -> assets/bd-<name>.mp4.

    Every chunk of edl.json (speech and declared pauses, which become black frames) is cut by frame count, so the
    region has exactly the frames of camera-src.mp4. Rebuilt when edl.json is newer or the crop/filters changed."""
    work = Path(work).resolve()
    a = work / "composition/assets"
    edl = json.loads((work / "edl.json").read_text())
    fps = edl["fps"]
    src = Path(source or edl["source"])
    w, h, x, y = _parse_crop(crop)
    chain = f"crop={w}:{h}:{x}:{y}" + (f",{vf}" if vf else "") + ",format=yuv420p"
    out, meta = a / f"bd-{name}.mp4", a / f"bd-{name}.json"
    sig = {"crop": chain, "source": str(src), "chunks": [[c.get("source_in"), c["out_start"], c["out_end"]]
                                                         for c in edl["chunks"]]}
    if out.exists() and meta.exists() and json.loads(meta.read_text()) == sig and not stale(out, work / "edl.json"):
        return out.name
    tmp = work / "clips"
    tmp.mkdir(exist_ok=True)
    parts = []
    for i, c in enumerate(edl["chunks"]):
        n = max(1, round((c["out_end"] - c["out_start"]) * fps))
        p = tmp / f"bd-{name}-{i:03d}.mp4"
        if c.get("pause") or c.get("source_in") is None:
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={fps}",
                 "-frames:v", n, "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", crf, "-preset", "fast", p])
        else:
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{c['source_in']:.4f}", "-i", src, "-vf", chain, "-an",
                 "-frames:v", n, "-r", fps, "-c:v", "libx264", "-crf", crf, "-preset", "fast", p])
        parts.append(p)
    lst = tmp / f"bd-{name}-list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
    for p in parts:
        p.unlink(missing_ok=True)
    meta.write_text(json.dumps(sig))
    return out.name


def external_clip(work, name, src, vf="", crf=17):
    """Copy an external clip (screen recording of the post, launch video) as assets/bd-<name>.mp4, 30 fps, no audio."""
    a = Path(work) / "composition/assets"
    out = a / f"bd-{name}.mp4"
    if stale(out, src):
        chain = (vf + "," if vf else "") + "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30,format=yuv420p"
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", chain, "-an", "-c:v", "libx264", "-crf", crf,
             "-preset", "medium", out])
    return out.name


def image_backdrop(work, name, src, max_height=14000):
    """Copy a still (screenshot, full-page capture) as assets/bd-<name>.<ext>, clipped to max_height px."""
    from PIL import Image
    a = Path(work) / "composition/assets"
    src = Path(src)
    out = a / f"bd-{name}{'.png' if src.suffix.lower() == '.png' else '.jpg'}"
    if stale(out, src):
        with Image.open(src) as im:
            im = im.convert("RGB")
            if im.size[1] > max_height:
                im = im.crop((0, 0, im.size[0], max_height))
            im.save(out, quality=93) if out.suffix == ".jpg" else im.save(out, optimize=True)
    return out.name


def fill_layer(work, name, kind):
    """Blurred, darkened cover copy of a backdrop (shown where the sharp layer does not reach the frame edges)."""
    a = Path(work) / "composition/assets"
    if kind == "image":
        from PIL import Image, ImageEnhance, ImageFilter
        src = next(a.glob(f"bd-{name}.*g"))
        out = a / f"bd-{name}-fill.jpg"
        if stale(out, src):
            with Image.open(src) as im:
                im = im.convert("RGB")
                w, h = im.size
                top = im.crop((0, 0, w, min(h, round(w * 16 / 9))))
                top = top.resize((270, 480))
                top = top.filter(ImageFilter.GaussianBlur(18))
                top = ImageEnhance.Color(top).enhance(0.45)
                top = ImageEnhance.Brightness(top).enhance(0.5)
                top.resize((1080, 1920), Image.BICUBIC).save(out, quality=86)
        return out.name
    src = a / f"bd-{name}.mp4"
    out = a / f"bd-{name}-fill.mp4"
    if stale(out, src):
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf",
             "scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=18:3,eq=brightness=-0.42:"
             "saturation=0.3,scale=540:960,format=yuv420p", "-an", "-c:v", "libx264", "-crf", "26", "-preset", "fast",
             out])
    return out.name


def last_frame(work, name):
    """Last frame of a video backdrop as JPEG (held under the video, so the subject stays after the clip ends)."""
    a = Path(work) / "composition/assets"
    src, out = a / f"bd-{name}.mp4", a / f"bd-{name}-last.jpg"
    if stale(out, src):
        run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.1", "-i", src, "-frames:v", "1", "-q:v", "3", out])
    return out.name


def still(video, t, out):
    """One frame of a video as PNG (e.g. to freeze the post for the hook or to read box coordinates)."""
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{float(t):.3f}", "-i", video, "-frames:v", "1", out])
    return Path(out)


# ------------------------------------------------------------------ capture a page
CONSENT_SELECTORS = ("#onetrust-banner-sdk", "#onetrust-consent-sdk", "#CybotCookiebotDialog", ".cc-window",
                     "[id*='cookie-banner']", "[class*='cookie-banner']", "[id*='consent-banner']",
                     "[class*='CookieConsent']", "[aria-label*='cookie' i][role='dialog']")


def capture(url, out, width=430, height=932, scale=2, mobile=True, dark=False, full_page=True, wait=2.5,
            selector=None, hide=(), max_height=14000, timeout=45, consent=True):
    """Screenshot of a public page with Playwright (Chromium). Mobile viewport by default (430x932 @2x = 860 px wide,
    sharp in a 1080 frame); full_page captures the whole length for a scrolled backdrop. Returns (w, h).
    Always look at the capture: error pages, bot walls, login walls and leftover banners happen; then use a
    screenshot or a screen recording from the user instead."""
    from playwright.sync_api import sync_playwright
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        kw = dict(viewport={"width": width, "height": height}, device_scale_factor=scale, locale="pt-BR",
                  color_scheme="dark" if dark else "light")
        if mobile:
            kw.update(is_mobile=True, has_touch=True, user_agent=MOBILE_UA)
        ctx = browser.new_context(**kw)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        try:
            page.wait_for_load_state("networkidle", timeout=timeout * 1000)
        except Exception:
            pass
        page.wait_for_timeout(int(wait * 1000))
        if consent:   # dismiss cookie walls: click a reject/accept button, then hide the usual containers
            for label in ("Reject All", "Rejeitar todos", "Rejeitar", "Accept All", "Aceitar todos", "Aceitar",
                          "Accept", "I agree", "Concordo", "OK"):
                try:
                    b = page.get_by_role("button", name=label, exact=True)
                    if b.count():
                        b.first.click(timeout=1500)
                        page.wait_for_timeout(400)
                        break
                except Exception:
                    pass
            hide = tuple(hide) + CONSENT_SELECTORS
        css = "".join(f"{s}{{display:none!important}}" for s in hide if s)
        css += "*{caret-color:transparent!important}"
        page.add_style_tag(content=css)
        if full_page:   # lazy images: walk the page once before the capture
            page.evaluate("""async () => { const h = document.body.scrollHeight;
                for (let y = 0; y < h; y += innerHeight * 0.8) { scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); }
                scrollTo(0, 0); }""")
            page.wait_for_timeout(600)
        if selector:
            page.locator(selector).first.screenshot(path=str(out))
        else:
            page.screenshot(path=str(out), full_page=full_page)
        browser.close()
    from PIL import Image
    with Image.open(out) as im:
        if im.size[1] > max_height * 1:
            im.crop((0, 0, im.size[0], max_height)).save(out)
        return Image.open(out).size


# ------------------------------------------------------------------ geometry
def view(src_w, src_h, focus, anchor_y=760, clamp=True, min_bottom=1300, max_top=0):
    """Transform (x, y, s) that shows `focus` = [cx, cy, w] of a backdrop (source px) with cx,cy at (540, anchor_y)
    and about `w` source px across the 1080 px frame.

    With clamp the backdrop never leaves an empty band: it always covers the width and the top of the frame, and it
    reaches at least `min_bottom` (the area under the speaker's head; below it the shade and the blurred fill take
    over). A page taller than the frame covers it entirely and is clamped at its top and bottom while it scrolls.
    So `w` is a wish: a landscape recording (1362x1194) cannot be shown narrower than its height allows.
    `max_top` > 0 lets the backdrop start lower (the band above is the 0-270 atmosphere zone, filled by the blurred
    copy), to bring the first lines of a page below the platform UI."""
    cx, cy, w = (float(v) for v in focus[:3])
    s = 1080.0 / w
    if clamp:
        s = max(s, 1080.0 / src_w, min_bottom / src_h)
    x, y = 540 - s * cx, anchor_y - s * cy
    if clamp:
        x = min(0.0, max(1080 - s * src_w, x))
        lower = (1920 if s * src_h >= 1920 else min_bottom) - s * src_h
        y = min(float(max_top), max(lower, y))
    return round(x, 2), round(y, 2), round(s, 5)


SPEAKER_STATES = {   # name: (size, face_x, face_y) on the 1080x1920 frame; size 1.0 = camera as wide as the frame
    "center": (0.95, 540, 1320), "right": (0.88, 720, 1340), "left": (0.88, 360, 1340),
    "small": (0.66, 800, 1450), "low": (0.85, 600, 1430), "hero": (1.12, 540, 1270), "punch": (1.32, 540, 1230)}


def speaker_states(face_x, face_y, cam_w, cam_h, extra=None):
    """States of the cutout container (origin 0 0): the median face of the take placed at a target point.

    face_x/face_y in camera px. Each state is (size, face_x_target, face_y_target): size 1.0 = the camera as wide
    as the frame. The bottom of the camera is pulled down to at least y 1600 (the body never floats above the UI
    zone; its lower edge fades out in the page). Returns {name: {x, y, s, face_y, bottom}}."""
    base = dict(SPEAKER_STATES)
    base.update(extra or {})
    st = {}
    for k, (size, fx_target, fy_target) in base.items():
        s = size * 1080 / cam_w
        y = fy_target - s * face_y
        if y + s * cam_h < 1600:
            y = 1600 - s * cam_h
        st[k] = {"x": round(fx_target - s * face_x, 1), "y": round(y, 1), "s": round(s, 5),
                 "face_y": round(y + s * face_y, 1), "bottom": round(y + s * cam_h, 1)}
    return st


GRADE = "eq=contrast=1.04:saturation=1.06:gamma=0.98,unsharp=5:5:0.35:5:5:0"


def speaker_cutout(work, keep=(1, 2, 3, 4, 5), matte_width=720, grade=GRADE, alpha_width=1080):
    """camera-hd.mp4 (camera-src at its own size, lightly graded) and camera-alpha.webm (the speaker cut out).

    The matte runs on a matte_width copy (MediaPipe multiclass: hair, skin, clothes, accessories), then is scaled
    up, clamped (H.264 brings the background back at ~10-40) and merged with the RGB at `alpha_width` (default
    1080: a 1440 px VP9 alpha video made the render Chrome crash on a 4-core/8 GB host; the largest state, punch,
    upscales it ~1.3x). Keep class 5 (accessories): glasses live there and their rims turn transparent without it;
    drop it (keep=(1, 2, 3, 4)) only when a mic arm or headphones stand out of the silhouette. Each stage is cached
    with its parameters. Cost on 4 cores: ~1/3 real time for the matte plus the VP9 alpha encode.
    Returns the size of camera-alpha.webm (the speaker element)."""
    import depthkit as dk
    a = Path(work) / "composition/assets"
    src, hd, alpha = a / "camera-src.mp4", a / "camera-hd.mp4", a / "camera-alpha.webm"
    w, h, _ = probe(src)
    if stale(hd, src):
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"{grade},format=yuv420p", "-an", "-c:v", "libx264",
             "-preset", "medium", "-crf", "15", "-g", "30", hd])
    aw = _even(min(alpha_width, w))
    ah = _even(h * aw / w)
    mask, mask_meta, meta = a / "matte-person.mp4", a / "matte-person.json", a / "camera-alpha.json"
    msig = {"keep": sorted(keep), "matte_width": matte_width, "grade": grade}
    if stale(mask, hd) or not mask_meta.exists() or json.loads(mask_meta.read_text()) != msig:
        mh = _even(h * matte_width / w)
        small = a / "camera-matte-src.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-i", hd, "-vf", f"scale={matte_width}:{mh}:flags=bicubic,format=yuv420p",
             "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", small])
        (a / "alpha-small.webm").unlink(missing_ok=True)
        dk.person_matte(work, video=small.name, name="alpha-small", keep_classes=set(keep))
        for f in (small, a / "alpha-small.webm"):
            f.unlink(missing_ok=True)
        mask_meta.write_text(json.dumps(msig))
    sig = dict(msig, alpha_width=aw)
    if not stale(alpha, mask) and meta.exists() and json.loads(meta.read_text()) == sig:
        return aw, ah
    run(["ffmpeg", "-v", "error", "-y", "-i", hd, "-i", mask, "-filter_complex",
         f"[0:v]scale={aw}:{ah}:flags=lanczos,format=rgba[c];"
         f"[1:v]format=gray,lut=c0='clip((val-34)*1.5,0,255)',scale={aw}:{ah}:flags=bicubic,gblur=sigma=0.9,"
         "lut=c0='clip((val-8)*1.05,0,255)'[m];[c][m]alphamerge,format=yuva420p[v]",
         "-map", "[v]", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "24",
         "-row-mt", "1", "-deadline", "good", "-cpu-used", "5", "-metadata:s:v:0", "alpha_mode=1", alpha], timeout=7200)
    meta.write_text(json.dumps(sig))
    return aw, ah


def speaker_top(work, mask="matte-person.mp4", samples=9, thr=128, min_frac=0.02):
    """Median first row of the speaker (hair top) in camera px, read from the matte (for QA of marks)."""
    import numpy as np
    a = Path(work) / "composition/assets"
    w, h, dur = probe(a / mask)
    tops = []
    for i in range(samples):
        t = (dur or 1) * (i + 0.5) / samples
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(a / mask), "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"], capture_output=True, check=True).stdout
        m = np.frombuffer(raw, np.uint8)[: w * h].reshape(h, w)
        rows = np.where((m > thr).sum(1) > w * min_frac)[0]
        if len(rows):
            tops.append(rows[0] / h)
    return float(np.median(tops)) if tops else 0.12


def freeze_alpha(work, video="camera-alpha.webm", out="speaker-last.png", back=0.08):
    """Last frame of the alpha video as a transparent PNG (the speaker stays on the CTA)."""
    a = Path(work) / "composition/assets"
    dst = a / out
    if stale(dst, a / video):
        run(["ffmpeg", "-v", "error", "-y", "-c:v", "libvpx-vp9", "-sseof", f"-{back}", "-i", a / video,
             "-frames:v", "1", "-pix_fmt", "rgba", dst])
    return dst.name


def _cli(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd == "capture":
        pos, kw = [], {}
        i = 0
        while i < len(args):
            a = args[i]
            if a == "--desktop":
                kw.update(mobile=False, width=kw.get("width", 1280), height=kw.get("height", 900), scale=kw.get("scale", 1))
            elif a == "--dark":
                kw["dark"] = True
            elif a == "--viewport":
                kw["full_page"] = False
            elif a in ("--width", "--height", "--max-height"):
                kw[a[2:].replace("-", "_")] = int(args[i + 1]); i += 1
            elif a in ("--scale", "--wait"):
                kw[a[2:]] = float(args[i + 1]); i += 1
            elif a == "--selector":
                kw["selector"] = args[i + 1]; i += 1
            elif a == "--hide":
                kw["hide"] = tuple(args[i + 1].split(",")); i += 1
            else:
                pos.append(a)
            i += 1
        if len(pos) != 2:
            print("usage: heditor capture <url> <out.png> [options]")
            return 2
        size = capture(pos[0], pos[1], **kw)
        print(json.dumps({"out": str(Path(pos[1]).resolve()), "width": size[0], "height": size[1]}))
        return 0
    if cmd == "region":
        if len(args) < 3:
            print("usage: heditor region <work> <name> <crop=w:h:x:y> [ffmpeg filters]")
            return 2
        name = region_clip(args[0], args[1], args[2], args[3] if len(args) > 3 else "")
        print(json.dumps({"out": name, "size": probe(Path(args[0]) / "composition/assets" / name)[:2]}))
        return 0
    print(f"unknown command {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
