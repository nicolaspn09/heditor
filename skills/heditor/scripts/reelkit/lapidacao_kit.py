"""Assets for the style `lapidacao` (imported by templates/styles/lapidacao/build.py through HEDITOR_KIT).

- grade + presenter matte: camera-hd.mp4 (neutral-cool grade) and camera-alpha.webm (MediaPipe multiclass matte
  computed at 720 px, levels clamped so the room never ghosts through, static garbage mask around the speaker,
  alpha merged with the full-resolution RGB);
- rig states and the garbage mask from the median face position (rk.track_faces);
- the object photos (raw stone, cut gem, case closed/open, velvet rope) prepared with soft elliptical alpha so
  they melt into the black atelier, plus a dull "raw" version of the stone;
- synthesised SFX (numpy) and the Mixkit tracks/SFX the style uses, downloaded once into
  ~/.heditor/assets/lapidacao (Mixkit Free License, provenance in mixkit.json).
Nothing here is specific to one video.
"""
import json
import os
import subprocess
import wave
from pathlib import Path

import numpy as np

HOME = Path(os.environ.get("HEDITOR_HOME", Path.home() / ".heditor"))
CACHE = HOME / "assets" / "lapidacao"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
SR = 48000

# neutral-cool grade: no yellow cast, black t-shirts stay black (compare 3-4 grades by vision on a new source)
GRADE = ("colortemperature=temperature=6800,colorbalance=rs=0.018:bs=-0.045,"
         "curves=all='0/0 0.07/0.02 0.5/0.495 0.85/0.88 1/1',eq=contrast=1.055:saturation=0.86:brightness=0.01,"
         "unsharp=5:5:0.35:5:5:0")

# Mixkit Free License (https://mixkit.co/license/). id -> (kind, title, role)
MIXKIT = {
    "m107": ("music", "Atoms in Peace (Alejandro Magaña)", "alternative bed: energy jump at 29 s, bass-heavy (presence share ~0.05)"),
    "m179": ("music", "Solitude (Alejandro Magaña)", "CTA: powerful, confident"),
    "s2538": ("sfx", "Hard laptop keyboard typing", "typing"), "s1387": ("sfx", "Fast keyboard typing", "typing"),
    "s1112": ("sfx", "Positive interface click", "click"), "s2541": ("sfx", "Single key press in a laptop", "click"),
    "s1120": ("sfx", "Modern click box check", "click"), "s2585": ("sfx", "On or off light switch tap", "switch"),
    "s677": ("sfx", "Cinematic glass hit suspense", "glass"), "s563": ("sfx", "Drum deep impact", "impact"),
    "s549": ("sfx", "Deep cinematic subtle drum impact", "impact"), "s1530": ("sfx", "Paper slide", "paper"),
    "s1104": ("sfx", "Page turn single", "paper"), "s1105": ("sfx", "Big paper page turn", "paper"),
    "s869": ("sfx", "Fairy sparkle whoosh", "sparkle"), "s1465": ("sfx", "Vacuum swoosh transition", "vacuum"),
    "s1466": ("sfx", "Elevating swoosh", "lift"), "s2857": ("sfx", "Gear fast lock tap", "lock"),
    "s1924": ("sfx", "Gate latch click", "lock"), "s1440": ("sfx", "Classic camera click", "shutter"),
    "s2602": ("sfx", "Electronics power up", "power_up"), "s2578": ("sfx", "Opening software interface", "ui"),
    "s939": ("sfx", "Christmas magic bell hit", "bell"), "s2995": ("sfx", "Stapling paper", "staple"),
}

OBJECT_PROMPTS = {
    "raw_stone.png": "Luxury jewelry commercial product photograph. A single ROUGH, UNCUT raw diamond crystal in its "
                     "natural state: irregular shape, frosted cloudy surface, natural uneven faces, rough edges. It "
                     "rests on a small patch of deep black velvet. Pure black background. One dramatic cool-white "
                     "spotlight from above. Macro lens, razor sharp, neutral colour, no warm or yellow cast. Square, "
                     "the stone centered at about 50% of the frame width. No text, no letters, no logos.",
    "cut_diamond.png": "(edit of raw_stone.png) Transform the rough stone into a flawless polished brilliant-cut "
                       "diamond, same size, position and scale, same black velvet, pure black background and "
                       "cool-white spotlight; crisp facets, white sparkle, subtle spectral fire; no text.",
    "box_closed.png": "Luxury jewelry commercial product photograph. A closed matte black rectangular presentation "
                      "box with thin champagne-gold metal edges and a small champagne-gold clasp, on black velvet, "
                      "three-quarter view from slightly above, pure black background, single cool-white spotlight, "
                      "neutral colour. Square, box centered at about 60% of the width. No text, no logos, no engraving.",
    "box_open.png": "(edit of box_closed.png) Same box, same angle, scale and lighting, lid OPEN, black velvet "
                    "interior with compartments, one larger central slot with a soft cool glow; no text.",
    "rope.png": "Luxury VIP entrance product photograph: two polished champagne-gold stanchions with a thick deep "
                "black velvet rope hanging between them, front view, black floor fading into a pure black "
                "background, single cool-white spotlight, neutral colour. Landscape. No text, no signs, no people.",
}


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def stale(out, src):
    out, src = Path(out), Path(src)
    return not out.exists() or (src.exists() and out.stat().st_mtime < src.stat().st_mtime)


# ------------------------------------------------------------------ downloads (Mixkit, cached once)
def mixkit(key):
    """Local path of a Mixkit preview (music m<id> or sfx s<id>), downloaded into the cache on first use."""
    kind = "music" if key.startswith("m") else "sfx"
    num = key[1:]
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{key}.mp3"
    if not path.exists() or path.stat().st_size < 2000:
        url = (f"https://assets.mixkit.co/music/{num}/{num}.mp3" if kind == "music"
               else f"https://assets.mixkit.co/active_storage/sfx/{num}/{num}-preview.mp3")
        run(["curl", "-sSfL", "-A", UA, "-o", str(path), url])
        prov = CACHE / "mixkit.json"
        data = json.loads(prov.read_text()) if prov.exists() else {}
        title = MIXKIT.get(key, (kind, "", ""))[1]
        data[key] = {"url": url, "title": title, "license": "Mixkit Free License", "bytes": path.stat().st_size}
        prov.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return str(path)


# ------------------------------------------------------------------ face, rig, matte
def face_median(work, rk):
    faces = rk.track_faces(work, step=0.25)
    xs = [f["x"] for f in faces if f.get("x") is not None]
    ys = [f["y"] for f in faces if f.get("y") is not None]
    if not xs:
        return 540.0, 1150.0
    return float(np.median(xs)) * 1080, float(np.median(ys)) * 1920


def rig_states(fx, fy):
    """Presenter container states (#prig holds the 1080x1920 plate + alpha, origin 0 0). The hair top is estimated
    at 0.278 H above the face centre (seated speaker, mid-chest framing); check the previews and adjust."""
    ht = fy - 0.278 * 1920
    st = {}
    for name, s, cx, top in (("full", 0.78, 540, 330), ("right", 0.62, 740, 330), ("left", 0.62, 340, 330),
                             ("low", 0.50, 540, 607)):
        st[name] = {"x": round(cx - s * fx, 1), "y": round(top - s * ht, 1), "scale": s}
    return st


def make_garbage(path, fx, fy):
    """White where the speaker can be (head ellipse + everything below the shoulders), feathered."""
    from PIL import Image, ImageFilter
    yy, xx = np.mgrid[0:1920, 0:1080]
    head = ((xx - (fx + 20)) / 440.0) ** 2 + ((yy - (fy - 218)) / 480.0) ** 2 <= 1.0
    body = yy >= fy - 388
    m = ((head | body) * 255).astype("uint8")
    Image.fromarray(m, "L").filter(ImageFilter.GaussianBlur(14)).save(path)


def camera_and_matte(work, rk, fx, fy, keep=(1, 2, 3, 4, 5)):
    """camera-hd.mp4 (graded) and camera-alpha.webm, rebuilt only when camera-src.mp4 is newer."""
    import depthkit as dk
    a = Path(work) / "composition/assets"
    src, hd, alpha = a / "camera-src.mp4", a / "camera-hd.mp4", a / "camera-alpha.webm"
    if stale(hd, src):
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", GRADE + ",format=yuv420p", "-an", "-c:v", "libx264",
             "-preset", "medium", "-crf", "14", "-g", "30", str(hd)])
    if not stale(alpha, hd):
        return
    m720 = a / "camera-m720.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(hd), "-vf", "scale=720:1280:flags=bicubic,format=yuv420p", "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "16", str(m720)])
    dk.person_matte(work, video="camera-m720.mp4", name="alpha720", keep_classes=set(keep))
    garbage = a / "matte-garbage.png"
    make_garbage(garbage, fx, fy)
    # H.264 brings the matte background back at ~10-12 and soft room residues up to ~40: clamp the levels so the room
    # never ghosts through, soften the edge, multiply by the garbage mask, merge with the full-resolution RGB.
    run(["ffmpeg", "-v", "error", "-y", "-i", str(hd), "-i", str(a / "matte-person.mp4"), "-loop", "1", "-i", str(garbage),
         "-filter_complex",
         "[1:v]format=gray,lut=c0='clip((val-38)*1.6,0,255)',scale=1080:1920:flags=bicubic,gblur=sigma=1.1,"
         "lut=c0='clip((val-10)*1.06,0,255)'[m0];[2:v]format=gray[g];[m0][g]blend=all_mode=multiply:shortest=1[m];"
         "[0:v]format=rgba[c];[c][m]alphamerge,format=yuva420p[v]",
         "-map", "[v]", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "24",
         "-row-mt", "1", "-deadline", "good", "-cpu-used", "4", "-metadata:s:v:0", "alpha_mode=1", str(alpha)])
    for f in (m720, a / "alpha720.webm"):
        f.unlink(missing_ok=True)


# ------------------------------------------------------------------ object photos
SPECS = [("raw_stone.png", "obj-stone.png", 0.50, 0.50, 0.40, 0.40, 760),
         ("cut_diamond.png", "obj-diamond.png", 0.50, 0.52, 0.38, 0.38, 760),
         ("box_closed.png", "obj-box-closed.png", 0.50, 0.49, 0.52, 0.46, 820),
         ("box_open.png", "obj-box-open.png", 0.50, 0.43, 0.54, 0.56, 820),
         ("rope.png", "obj-rope.png", 0.50, 0.55, 0.47, 0.47, 900)]


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def objects(work):
    """<work>/gen/*.png (generated without text; prompts in OBJECT_PROMPTS) -> composition/assets/obj-*.png."""
    from PIL import Image, ImageFilter
    gen, a = Path(work) / "gen", Path(work) / "composition/assets"
    missing = [s for s, *_ in SPECS if not (gen / s).exists()]
    if missing:
        prompts = "\n".join(f"- {m}: {OBJECT_PROMPTS[m]}" for m in missing)
        raise SystemExit(f"lapidacao: generate the object photos into {gen}/ first (image tool, no text):\n{prompts}")
    for src, out, cx, cy, rx, ry, width in SPECS:
        if not stale(a / out, gen / src):
            continue
        im = Image.open(gen / src).convert("RGB")
        w, h = im.size
        arr = np.asarray(im).astype(np.float32) / 255.0
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt(((xx / w - cx) / rx) ** 2 + ((yy / h - cy) / ry) ** 2)
        alpha = 1 - _smooth(0.72, 1.0, d)
        vig = 1 - 0.55 * _smooth(0.45, 1.0, d)
        arr = np.clip((arr - 0.045) / 0.955, 0, 1) ** 1.12
        rgba = np.dstack([arr * vig[..., None], alpha]) * 255
        img = Image.fromarray(rgba.astype("uint8"), "RGBA").resize((width, round(width * h / w)), Image.LANCZOS)
        img.save(a / out, optimize=True)
    raw = a / "obj-stone-raw.png"
    if stale(raw, a / "obj-stone.png"):
        rgba = np.asarray(Image.open(a / "obj-stone.png").convert("RGBA")).astype(np.float32)
        c, al = rgba[..., :3] / 255.0, rgba[..., 3:4]
        c = c.mean(2, keepdims=True) * 0.85 + c * 0.15          # almost grey
        c = (0.10 + (c - 0.10) * 0.55) * 0.78                    # flat, dull: it must read as raw
        c = np.clip(c + np.random.default_rng(7).normal(0, 0.035, c.shape[:2])[..., None] * (c > 0.06), 0, 1)
        Image.fromarray(np.dstack([c * 255, al]).astype("uint8"), "RGBA").filter(ImageFilter.GaussianBlur(1.2)).save(raw)


# ------------------------------------------------------------------ synthesised SFX
def _t(d):
    return np.arange(int(d * SR)) / SR


def _lp(x, a):
    y, acc = np.empty_like(x), 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def _band(d, lo, hi, rng):
    n = rng.standard_normal(int(d * SR))
    return _lp(n, hi) - _lp(n, lo)


def _write(path, x):
    x = np.asarray(x, np.float64)
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.89
    d = int(0.0006 * SR)
    st = np.column_stack([x, np.concatenate([np.zeros(d), x[:-d]]) * 0.75 + x * 0.25])
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype("<i2").tobytes())


def synth(out_dir):
    """Sub thump, crystal tings, laser sweep, grinder, CRT power-down, risers, ticks, shimmer, spotlight clunk, case
    slam and a velvet whoosh, described by construction (nobody listens during the build)."""
    out = Path(out_dir)
    if (out / "velvet_whoosh.wav").exists():
        return out
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261021)

    def sub(d=0.7, f0=62, f1=34):
        t = _t(d)
        f = f1 + (f0 - f1) * np.exp(-t / 0.08)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18) + _band(d, .02, .35, rng) * np.exp(-t / .006) * .35

    def crystal(base, k0):
        t = _t(1.6)
        x = sum(a * np.sin(2 * np.pi * base * r * (1 + .002 * (k + k0)) * t + k) * np.exp(-t / tau)
                for k, (r, a, tau) in enumerate([(1, 1, .55), (2.76, .55, .38), (5.4, .35, .22), (8.93, .18, .12)]))
        return x * (1 - np.exp(-t / .002))

    def tick(d=0.09):
        t = _t(d)
        return (np.sin(2 * np.pi * 1850 * t) * .6 + _band(d, .2, .9, rng) * .4) * np.exp(-t / .012)

    def riser(d):
        t = _t(d)
        f = 300 + 1800 * (t / d) ** 2
        return (_band(d, .01, .6, rng) * .8 + np.sin(2 * np.pi * np.cumsum(f) / SR) * .15) * (t / d) ** 2.2 * np.minimum(1, (d - t) / .02)

    t = _t(1.9)
    f = 900 + 2600 * (t / 1.9) ** 1.4
    laser = ((np.sin(2 * np.pi * np.cumsum(f) / SR) * .35 + _band(1.9, .25, .9, rng) * .5) * (.75 + .25 * np.sin(2 * np.pi * 31 * t))
             * np.minimum(1, t / .08) * np.minimum(1, (1.9 - t) / .25))
    t2 = _t(2.2)
    grind = _band(2.2, .04, .5, rng) * (.6 + .4 * np.abs(np.sin(2 * np.pi * 23 * t2))) * np.minimum(1, t2 / .15) * np.minimum(1, (2.2 - t2) / .3)
    t3 = _t(.55)
    pdown = np.sin(2 * np.pi * np.cumsum(60 + 900 * np.exp(-t3 / .12)) / SR) * np.exp(-t3 / .22) + _band(.55, .05, .6, rng) * np.exp(-t3 / .05) * .2
    ticks = np.zeros(int(6 * SR))
    for i, s in enumerate(np.arange(0, 5.9, .5)):
        k = tick() * (1 if i % 2 == 0 else .7)
        j = int(s * SR)
        ticks[j:j + len(k)] += k
    t4 = _t(2.2)
    shimmer = sum(np.sin(2 * np.pi * f * t4 + f) * (.5 + .5 * np.sin(2 * np.pi * (7 + f / 900) * t4)) for f in (3520, 4186, 4699, 5274, 6272))
    shimmer *= np.minimum(1, t4 / .25) * np.minimum(1, (2.2 - t4) / .8) * .3
    t5 = _t(.9)
    spot = sub(.9, 80, 40) * .8 + _band(.9, .05, .7, rng) * np.exp(-t5 / .25) * .25 + np.sin(2 * np.pi * 100 * t5) * .08 * np.minimum(1, t5 / .05) * np.exp(-t5 / .6)
    t6 = _t(.8)
    slam = sub(.8, 95, 45) + _band(.8, .03, .4, rng) * np.exp(-t6 / .03) * .7
    j = int(.11 * SR)
    lk = tick(.05) * .8
    slam[j:j + len(lk)] += lk
    t7 = _t(.9)
    velvet = _band(.9, .01, .18, rng) * np.sin(np.pi * np.clip(t7 / .9, 0, 1)) ** 1.5
    for name, x in (("sub_thump", sub()), ("sub_long", sub(1.4, 55, 28)), ("crystal_0", crystal(2350, 0)),
                    ("crystal_1", crystal(2790, 1)), ("crystal_2", crystal(3130, 2)), ("laser", laser), ("grind", grind),
                    ("power_down", pdown), ("riser", riser(1.2)), ("riser_short", riser(.55)), ("tick", tick()),
                    ("ticks", ticks), ("shimmer", shimmer), ("spot_on", spot), ("box_slam", slam), ("velvet_whoosh", velvet)):
        _write(out / f"{name}.wav", x)
    return out


def sfx_library(rk, work):
    """rk.sfx_library() + the style's Mixkit SFX (downloaded once) + synthesised sounds (<work>/sound/synth)."""
    lib = rk.sfx_library()
    sy = synth(Path(work) / "sound/synth")

    def add(name, files, trim):
        lib[name] = {"files": [str(f) for f in files], "trim": trim}

    mk = mixkit
    add("s_typing", [mk("s2538"), mk("s1387")], ("head", 3.0))
    add("s_click", [mk("s1112"), mk("s2541"), mk("s1120")], ("head", 0.25))
    add("s_switch", [mk("s2585")], ("head", 0.5))
    add("s_glass", [mk("s677")], ("head", 1.6))
    add("s_impact", [mk("s563"), mk("s549")], ("head", 1.4))
    add("s_paper", [mk("s1530"), mk("s1104"), mk("s1105")], ("head", 0.8))
    add("s_sparkle", [mk("s869")], ("head", 2.0))
    add("s_vacuum", [mk("s1465")], ("head", 1.6))
    add("s_lift", [mk("s1466")], ("head", 0.9))
    add("s_lock", [mk("s2857"), mk("s1924")], ("head", 0.4))
    add("s_shutter", [mk("s1440")], ("head", 0.5))
    add("s_power_up", [mk("s2602")], ("head", 1.4))
    add("s_ui", [mk("s2578")], ("head", 0.8))
    add("s_bell", [mk("s939")], ("head", 1.2))
    add("s_staple", [mk("s2995")], ("head", 0.4))
    for name, files, trim in (("s_spot", ["spot_on"], 0.9), ("s_sub", ["sub_thump", "sub_long"], 0.9),
                              ("s_power_down", ["power_down"], 0.55), ("s_crystal", ["crystal_0", "crystal_1", "crystal_2"], 1.4),
                              ("s_laser", ["laser"], 1.9), ("s_grind", ["grind"], 2.2), ("s_riser", ["riser", "riser_short"], 1.2),
                              ("s_tick", ["tick"], 0.1), ("s_ticks", ["ticks"], 6.0), ("s_shimmer", ["shimmer"], 2.2),
                              ("s_slam", ["box_slam"], 0.8), ("s_velvet", ["velvet_whoosh"], 0.9)):
        add(name, [sy / f"{f}.wav" for f in files], ("head", trim))
    return lib
