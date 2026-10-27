"""depthkit: person matte, depth map, plane mapping and point tracking for layered (2.5D/3D) edits.

These are the building blocks of the depth-layer techniques in `references/depth-and-3d.md`:
text behind the speaker, captions that belong to the set, depth-graded backgrounds, contour maps,
objects that pass between the speaker and the wall, and labels pinned to things in the room.

    import reelkit as rk, depthkit as dk
    dk.person_matte(work)                    # camera-alpha.webm (RGB untouched + alpha) + matte-person.mp4
    dk.depth_map(work)                       # depth.mp4 (near = white) + depth-still.png
    dk.plane_matrix3d(900, 300, quad)        # CSS matrix3d that pins a 900x300 element onto 4 points
    dk.track_points(work, 2.0, [(410, 620)]) # follows points in the camera video (labels pinned to objects)
    dk.still_layers("gen/scene.png", assets)  # background + soft front layer of a still for 2.5D parallax

Models (downloaded by setup / fetch_assets, or on first use):
- MediaPipe selfie multiclass segmenter 256x256 (Apache-2.0) for the person matte;
- Depth Anything V2 Small ONNX (Apache-2.0) for the depth map.
All outputs are derived frame for frame from the same camera file, so they stay in sync with it.
"""

import json
import subprocess
import urllib.request
from pathlib import Path

import numpy as np

from reelkit import ASSETS, MODELS, _stale

SEGMENTER_MODELS = {
    "multiclass": ("selfie_multiclass_256x256.tflite",
                   "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/"
                   "float32/latest/selfie_multiclass_256x256.tflite"),
    "selfie": ("selfie_segmenter.tflite",
               "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/"
               "float16/latest/selfie_segmenter.tflite"),
}
DEPTH_MODEL = ("depth_anything_v2_small.onnx",
               "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx")
HAND_MODEL = ("hand_landmarker.task",
              "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/"
              "hand_landmarker.task")


def _model(name, url):
    path = MODELS / name
    if not path.exists() or path.stat().st_size == 0:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "heditor/1.5 (+https://github.com/pycodebr/heditor)"})
        with urllib.request.urlopen(req, timeout=300) as r, tmp.open("wb") as f:
            while block := r.read(1 << 20):
                f.write(block)
        tmp.replace(path)
    return path


def setup_three(work):
    """Copy three.js (module + core, MIT) into <work>/composition/assets so 3D layers render offline:
    `import * as THREE from "./assets/three.module.min.js"` inside a <script type="module">."""
    a = Path(work) / "composition/assets"
    a.mkdir(parents=True, exist_ok=True)
    for name in ("js/three.module.min.js", "js/three.core.min.js", "licenses/three-LICENSE.txt"):
        src = ASSETS / name
        if not src.exists():
            raise FileNotFoundError(f"{src} missing: re-run setup.sh")
        if not (a / src.name).exists():
            (a / src.name).write_bytes(src.read_bytes())
    return a


def _probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                          "stream=width,height,r_frame_rate", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(num) / float(den)


def _reader(path, w, h, vf=None):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path)]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    proc.wait()


def _writer(path, w, h, fps, pix_in, args):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", pix_in, "-s", f"{w}x{h}",
           "-r", f"{fps:.6f}", "-i", "-"] + args + [str(path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def _sheet(frames, out, w=270):
    """Contact sheet of RGB frames (list of HxWx3 uint8) for vision QA."""
    import cv2
    tiles = []
    for f in frames:
        h = round(f.shape[0] * w / f.shape[1])
        tiles.append(cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA))
    row = np.concatenate([np.pad(t, ((4, 4), (4, 4), (0, 0)), constant_values=255) for t in tiles], axis=1)
    cv2.imwrite(str(out), cv2.cvtColor(row, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])


# ---------------------------------------------------------------- person matte

def alpha_floor(m, floor):
    """Remove the faint alpha a segmenter leaves over the whole background, keeping the edge gradient.

    a' = (a - floor) / (1 - floor), clipped to 0..1: everything at or below `floor` becomes fully transparent and the
    soft edge is stretched back to 0..1. Synthetic plates (AI avatars) showed a haze of ~0.04-0.07 that made the room
    show through as a ghost over graphic walls."""
    if not floor:
        return m
    return np.clip((m - floor) / (1.0 - floor), 0.0, 1.0)


def person_matte(work, video="camera-hd.mp4", name="camera-alpha", model="multiclass", ema=0.4,
                 radius=6, eps=2e-3, gamma=1.25, erode=1, keep_classes=None, crf=26, floor=0.09):
    """Alpha matte of the speaker, frame for frame with `video`.

    Writes into <work>/composition/assets:
      <name>.webm      VP9 + alpha (yuva420p): the camera RGB untouched, background transparent
      matte-person.mp4 the matte as greyscale (white = person), for ffmpeg composites/QA
    and <work>/qa/matte-sheet.jpg (six frames over magenta) + qa/matte-stats.json.

    model="multiclass" keeps hair, skin, clothes and accessories (classes 1-5); pass keep_classes to drop
    some (e.g. {1, 2, 3, 4} drops accessories such as a microphone arm). ema smooths flicker over time,
    the guided filter (radius/eps) snaps the edge to the RGB, gamma tightens the soft halo, erode shrinks
    the edge by N px to remove background fringe, floor removes the faint alpha left over the whole background
    (qa/matte-stats.json reports it as background_haze, measured before the floor).
    """
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    a = Path(work) / "composition/assets"
    src = a / video
    out_webm, out_mask = a / f"{name}.webm", a / "matte-person.mp4"
    if not _stale(out_webm, src) and not _stale(out_mask, src):
        return json.loads((Path(work) / "qa/matte-stats.json").read_text())
    w, h, fps = _probe(src)
    fname, url = SEGMENTER_MODELS[model]
    seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=BaseOptions(model_asset_path=str(_model(fname, url))),
        running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True, output_category_mask=False))
    keep = keep_classes or ({1, 2, 3, 4, 5} if model == "multiclass" else {0})
    webm = _writer(out_webm, w, h, fps, "rgba", ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
                                                 "-b:v", "0", "-crf", str(crf), "-row-mt", "1", "-deadline", "good",
                                                 "-cpu-used", "4", "-metadata:s:v:0", "alpha_mode=1"])
    mask = _writer(out_mask, w, h, fps, "gray", ["-c:v", "libx264", "-preset", "medium", "-crf", "16",
                                                 "-pix_fmt", "yuv420p"])
    prev, cover, picks, n, haze = None, [], [], 0, []
    kernel = np.ones((3, 3), np.uint8)
    for i, frame in enumerate(_reader(src, w, h)):
        res = seg.segment_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame)),
                                    int(i * 1000 / fps))
        conf = [m.numpy_view() for m in res.confidence_masks]
        p = sum(conf[c] for c in keep) if model == "multiclass" else conf[0]
        p = cv2.resize(np.clip(p, 0, 1).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        prev = p if prev is None else ema * prev + (1 - ema) * p
        guide = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
        m = cv2.ximgproc.guidedFilter(guide, prev, radius, eps) if radius else prev
        m = np.clip(m, 0, 1) ** gamma
        if i % max(1, int(fps)) == 0:
            low = m[m < 0.25]
            haze.append(float(np.median(low)) if low.size else 0.0)
        m = alpha_floor(m, floor)
        if erode:
            m = cv2.erode(m, kernel, iterations=erode)
        a8 = (m * 255 + 0.5).astype(np.uint8)
        webm.stdin.write(np.dstack([frame, a8]).tobytes())
        mask.stdin.write(a8.tobytes())
        cover.append(float(m.mean()))
        if i % max(1, int(fps * 2)) == 0 and len(picks) < 6:
            bg = np.zeros_like(frame); bg[:] = (255, 0, 255)
            picks.append((frame * m[..., None] + bg * (1 - m[..., None])).astype(np.uint8))
        n += 1
    seg.close()
    for p in (webm, mask):
        p.stdin.close(); p.wait()
    (Path(work) / "qa").mkdir(exist_ok=True)
    if picks:
        _sheet(picks, Path(work) / "qa/matte-sheet.jpg")
    cv = np.array(cover)
    jumps = [round(i / fps, 2) for i in np.where(np.abs(np.diff(cv)) > 0.04)[0]]
    stats = {"frames": n, "fps": fps, "coverage_mean": round(float(cv.mean()), 3),
             "coverage_min": round(float(cv.min()), 3), "coverage_max": round(float(cv.max()), 3),
             "coverage_jumps_s": jumps[:40], "model": model, "classes": sorted(keep),
             "background_haze": round(float(np.median(haze)), 3) if haze else None, "floor": floor}
    (Path(work) / "qa/matte-stats.json").write_text(json.dumps(stats, indent=1))
    return stats


# ---------------------------------------------------------------- depth

def depth_map(work, video="camera-hd.mp4", out="depth.mp4", fps=10, size=518, ema=0.5, still_at=0.0):
    """Relative depth (near = white) with Depth Anything V2 Small, sampled at `fps` and held to the
    source frame rate. Writes <assets>/<out>, <assets>/depth-still.png (frame at `still_at`) and
    qa/depth-sheet.jpg. Normalisation uses running 2nd/98th percentiles so the grey levels do not pump.

    Typical uses: contour/edge map of the room, depth fog or blur on the background only, depth-graded
    colour (near warm / far cold), parallax layers, and near/far measurement labels.
    """
    import cv2
    import onnxruntime as ort

    a = Path(work) / "composition/assets"
    src, dst = a / video, a / out
    if not _stale(dst, src):
        return dst.name
    w, h, src_fps = _probe(src)
    sess = ort.InferenceSession(str(_model(*DEPTH_MODEL)), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0].name
    sh = round(size * h / w / 14) * 14 if h > w else size
    sw = size if h > w else round(size * w / h / 14) * 14
    mean, std = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225], np.float32)
    tmp = a / f".{Path(out).stem}-lowfps.mp4"
    wr = _writer(tmp, w, h, fps, "gray", ["-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p"])
    lo = hi = None
    picks, still = [], None
    for i, frame in enumerate(_reader(src, w, h, vf=f"fps={fps}")):
        x = cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        x = ((x - mean) / std).transpose(2, 0, 1)[None]
        d = sess.run(None, {inp: x})[0][0]
        q2, q98 = np.percentile(d, [2, 98])
        lo = q2 if lo is None else ema * lo + (1 - ema) * q2
        hi = q98 if hi is None else ema * hi + (1 - ema) * q98
        g = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
        g8 = (cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC) * 255 + 0.5).astype(np.uint8)
        wr.stdin.write(g8.tobytes())
        t = i / fps
        if still is None and t >= still_at:
            still = g8
        if i % max(1, fps * 2) == 0 and len(picks) < 6:
            picks.append(np.dstack([g8] * 3))
    wr.stdin.close(); wr.wait()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-vf", f"fps={src_fps:.6f},format=yuv420p",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "14", str(dst)], check=True)
    tmp.unlink(missing_ok=True)
    if still is not None:
        cv2.imwrite(str(a / "depth-still.png"), still)
    if picks:
        (Path(work) / "qa").mkdir(exist_ok=True)
        _sheet(picks, Path(work) / "qa/depth-sheet.jpg")
    return dst.name


def depth_look(work, name, vf_bg, vf_depth="", video="camera-hd.mp4", depth="depth.mp4", invert=False):
    """camera-<name>.mp4 = camera graded by depth: `vf_bg` is applied fully to the far parts and fades
    out towards the near parts (white in depth.mp4). Example: depth fog
        depth_look(work, "fog", "eq=brightness=-0.25:saturation=0.4,gblur=sigma=6")
    `vf_depth` reshapes the depth before use (e.g. "curves=all='0/0 0.55/0.2 1/1'" to protect only the speaker).
    """
    a = Path(work) / "composition/assets"
    dst = a / f"camera-{name}.mp4"
    if not _stale(dst, a / video) and not _stale(dst, a / depth):
        return dst.name
    d = "format=gray" + ("," + vf_depth if vf_depth else "") + (",negate" if invert else "")
    # maskedmerge takes the second input where the mask is white: near (white) keeps the original.
    fc = (f"[0:v]split[o][f];[f]{vf_bg}[far];[1:v]{d}[m];"
          f"[far][o][m]maskedmerge,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a / video), "-i", str(a / depth), "-filter_complex", fc,
                    "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-an", str(dst)],
                   check=True, timeout=1800)
    return dst.name


# ---------------------------------------------------------------- stills (2.5D parallax)

def front_alpha(depth, cut=0.52, soft=0.2, blur=6.0):
    """Soft alpha of the near planes of a relative depth map (any range; near = high).
    The depth is normalised by its 2nd/98th percentiles, `cut` is where the front starts, `soft` the width of
    the ramp and `blur` (sigma in px, 0 = none) softens the edge so the front never looks cut out."""
    d = np.asarray(depth, np.float32)
    lo, hi = np.percentile(d, [2, 98])
    g = np.clip((d - lo) / max(float(hi - lo), 1e-6), 0, 1)
    a = np.clip((g - cut) / max(soft, 1e-6), 0, 1)
    if blur:
        import cv2
        a = cv2.GaussianBlur(a, (0, 0), blur)
    return a


def still_layers(src, out_dir, cut=0.52, soft=0.2, blur=6.0, size=518, quality=88):
    """Background + soft front layer of a still image for 2.5D parallax (Ken Burns with the front moving more).
    Writes <out_dir>/<stem>.jpg (background), <stem>-front.webp (RGBA, near planes only) and <stem>-depth.png
    (relative depth, near = white). Depth Anything V2 Small, CPU. Skips the work when the outputs are newer."""
    import cv2
    import onnxruntime as ort
    from PIL import Image

    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    back, front, dpng = out_dir / f"{src.stem}.jpg", out_dir / f"{src.stem}-front.webp", out_dir / f"{src.stem}-depth.png"
    if not _stale(front, src) and not _stale(back, src):
        return back.name, front.name
    im = Image.open(src).convert("RGB")
    im.save(back, quality=90)
    rgb = np.asarray(im)
    h, w = rgb.shape[:2]
    sess = ort.InferenceSession(str(_model(*DEPTH_MODEL)), providers=["CPUExecutionProvider"])
    sh = round(size * h / w / 14) * 14 if h > w else size
    sw = size if h > w else round(size * w / h / 14) * 14
    mean, std = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225], np.float32)
    x = cv2.resize(rgb, (sw, sh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    x = ((x - mean) / std).transpose(2, 0, 1)[None]
    d = sess.run(None, {sess.get_inputs()[0].name: x})[0][0]
    d = cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)
    lo, hi = np.percentile(d, [2, 98])
    cv2.imwrite(str(dpng), (np.clip((d - lo) / max(float(hi - lo), 1e-6), 0, 1) * 255).astype(np.uint8))
    a = front_alpha(d, cut, soft, blur)
    Image.fromarray(np.dstack([rgb, (a * 255).astype(np.uint8)]), "RGBA").save(front, quality=quality, method=5)
    return back.name, front.name


# ---------------------------------------------------------------- planes and tracking

def homography(src_pts, dst_pts):
    """3x3 homography mapping 4 source points to 4 destination points."""
    A = []
    for (x, y), (u, v) in zip(src_pts, dst_pts):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(A, dtype=np.float64))
    H = vt[-1].reshape(3, 3)
    return H / H[2, 2]


def plane_matrix3d(w, h, quad):
    """CSS `matrix3d(...)` that maps an element of size w x h (transform-origin: 0 0) onto `quad`:
    four (x, y) stage points in order top-left, top-right, bottom-right, bottom-left.
    Use it to paint captions/titles on a wall, desk, screen, sign or floor of the camera image.
    Put the element inside the same container as the camera so punch-ins and shakes move both."""
    H = homography([(0, 0), (w, 0), (w, h), (0, h)], quad)
    m = [H[0, 0], H[1, 0], 0, H[2, 0], H[0, 1], H[1, 1], 0, H[2, 1], 0, 0, 1, 0, H[0, 2], H[1, 2], 0, H[2, 2]]
    return "matrix3d(" + ",".join(f"{v:.12g}" for v in m) + ")"


def track_points(work, t0, points, t1=None, video="camera-hd.mp4", step=1 / 30, out=None):
    """Follow points of the camera image (video pixels) from t0 to t1 with pyramidal Lucas-Kanade.
    Returns [{"t", "pts": [[x, y], ...], "ok": [bool, ...]}] and writes qa/track-<t0>.json.
    Use it to pin labels, arrows, tags or a plane quad to objects when the camera or the object moves.
    Lost points keep their last position (ok=false): check them before relying on the track."""
    import cv2
    a = Path(work) / "composition/assets"
    src = a / video
    w, h, fps = _probe(src)
    dur = None if t1 is None else max(step, t1 - t0)
    vf = f"fps={1 / step:.6f}"
    cmd_in = ["-ss", f"{t0:.3f}"] + (["-t", f"{dur:.3f}"] if dur else [])
    proc = subprocess.Popen(["ffmpeg", "-v", "error"] + cmd_in + ["-i", str(src), "-vf", vf + ",format=gray",
                                                                  "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    size = w * h
    prev = None
    pts = np.array(points, np.float32).reshape(-1, 1, 2)
    ok = np.ones(len(points), bool)
    res, i = [], 0
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        g = np.frombuffer(buf, np.uint8).reshape(h, w)
        if prev is not None:
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts, None, winSize=(31, 31), maxLevel=3,
                                                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
            good = st.reshape(-1).astype(bool)
            pts = np.where(good[:, None, None], nxt, pts)
            ok &= good
        res.append({"t": round(t0 + i * step, 3), "pts": pts.reshape(-1, 2).round(1).tolist(), "ok": ok.tolist()})
        prev, i = g, i + 1
    proc.wait()
    (Path(work) / "qa").mkdir(exist_ok=True)
    Path(out or Path(work) / f"qa/track-{t0:.2f}.json").write_text(json.dumps(res))
    return res


def to_stage(pt, video_size, box):
    """Video pixel -> stage pixel for a video drawn with object-fit: cover into box=(x, y, w, h)."""
    vw, vh = video_size
    x, y, bw, bh = box
    s = max(bw / vw, bh / vh)
    ox, oy = x + (bw - vw * s) / 2, y + (bh - vh * s) / 2
    return ox + pt[0] * s, oy + pt[1] * s


def track_hands(work, t0=0.0, t1=None, video="camera-hd.mp4", step=1 / 15, max_hands=2, out=None):
    """Hand landmarks (MediaPipe Hand Landmarker, 21 points per hand) in video pixels.

    Returns [{"t", "hands": [{"side": "Left|Right", "score", "pts": [[x, y], ...21], "palm": [x, y],
    "size": px}]}] and writes qa/hands-<t0>.json. `palm` is the centre of the wrist and the four knuckles
    (landmarks 0, 5, 9, 13, 17) and `size` the wrist→middle-knuckle distance, so an object that floats
    above the palm can be placed at palm - (0, 1.2 * size) and scaled with size. Frames without hands
    have an empty list: hold the last position for <= 0.3 s, then fade the object out."""
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    a = Path(work) / "composition/assets"
    src = a / video
    w, h, _ = _probe(src)
    det = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(_model(*HAND_MODEL))), running_mode=vision.RunningMode.VIDEO,
        num_hands=max_hands, min_hand_detection_confidence=0.4, min_tracking_confidence=0.4))
    dur = None if t1 is None else max(step, t1 - t0)
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}"] + (["-t", f"{dur:.3f}"] if dur else []) + [
        "-i", str(src), "-vf", f"fps={1 / step:.6f}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    res, i, size = [], 0, w * h * 3
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        frame = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        r = det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame)),
                                 int(i * step * 1000))
        hands = []
        for lm, hd in zip(r.hand_landmarks, r.handedness):
            pts = [[round(p.x * w, 1), round(p.y * h, 1)] for p in lm]
            palm = np.mean([pts[k] for k in (0, 5, 9, 13, 17)], axis=0)
            hands.append({"side": hd[0].category_name, "score": round(hd[0].score, 3), "pts": pts,
                          "palm": palm.round(1).tolist(),
                          "size": round(float(np.hypot(*np.subtract(pts[9], pts[0]))), 1)})
        res.append({"t": round(t0 + i * step, 3), "hands": hands})
        i += 1
    proc.wait()
    det.close()
    (Path(work) / "qa").mkdir(exist_ok=True)
    Path(out or Path(work) / f"qa/hands-{t0:.2f}.json").write_text(json.dumps(res))
    return res


# ---------------------------------------------------------------- stylised scans of the room

def _hex(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def edge_look(work, name="edges", color="#b46cff", source="depth", glow=3, keep_person=True, dim=0.12,
              video="camera-hd.mp4", depth="depth.mp4", matte="matte-person.mp4"):
    """camera-<name>.mp4: the room turned into glowing contour lines (a depth "scan").

    source="depth" draws iso-depth contours (clean, reads as a 3D scan), "rgb" uses Canny on the picture
    (more detail, busier). The background is dimmed to `dim`, lines are drawn in `color` with a soft glow
    and, with keep_person, the speaker stays in full colour on top (needs person_matte first)."""
    import cv2
    a = Path(work) / "composition/assets"
    src, dst = a / video, a / f"camera-{name}.mp4"
    deps = [src] + ([a / depth] if source == "depth" else []) + ([a / matte] if keep_person else [])
    if dst.exists() and not any(_stale(dst, d) for d in deps):
        return dst.name
    w, h, fps = _probe(src)
    col = np.array(_hex(color), np.float32)
    readers = [_reader(src, w, h)]
    if source == "depth":
        readers.append(_reader(a / depth, w, h))
    if keep_person:
        readers.append(_reader(a / matte, w, h))
    wr = _writer(dst, w, h, fps, "rgb24", ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p"])
    for frames in zip(*readers):
        frame = frames[0]
        if source == "depth":
            d = cv2.GaussianBlur(frames[1][..., 0], (0, 0), 2)
            bands = (d // 18).astype(np.uint8)
            lines = (cv2.morphologyEx(bands, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0).astype(np.float32)
            lines = np.maximum(lines, cv2.Canny(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), 80, 160).astype(np.float32)
                               / 255 * 0.35)
        else:
            lines = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), (0, 0), 1.2), 50, 120)
            lines = lines.astype(np.float32) / 255
        halo = cv2.GaussianBlur(lines, (0, 0), glow) * 2.2 if glow else 0
        ink = np.clip(lines + halo, 0, 1)[..., None]
        bg = frame.astype(np.float32) * dim
        out = bg * (1 - ink) + col * ink
        if keep_person:
            m = (frames[-1][..., :1].astype(np.float32) / 255)
            out = frame.astype(np.float32) * m + out * (1 - m)
        wr.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
    wr.stdin.close(); wr.wait()
    return dst.name


def dots_look(work, name="dots", color="#ff4fd8", step=9, keep_person=True, near_boost=1.6,
              video="camera-hd.mp4", depth="depth.mp4", matte="matte-person.mp4"):
    """camera-<name>.mp4: the background becomes a point cloud (dots on a grid, size and brightness by
    depth, tinted with `color`) on black, the speaker stays solid on top. Returns (file, points_per_frame)
    so the HUD can show a real point count."""
    import cv2
    a = Path(work) / "composition/assets"
    src, dst = a / video, a / f"camera-{name}.mp4"
    w, h, fps = _probe(src)
    ys, xs = np.mgrid[step // 2:h:step, step // 2:w:step]
    n_pts = int(xs.size)
    deps = [src, a / depth] + ([a / matte] if keep_person else [])
    if dst.exists() and not any(_stale(dst, d) for d in deps):
        return dst.name, n_pts
    col = np.array(_hex(color), np.float32) / 255
    readers = [_reader(src, w, h), _reader(a / depth, w, h)] + ([_reader(a / matte, w, h)] if keep_person else [])
    wr = _writer(dst, w, h, fps, "rgb24", ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p"])
    for frames in zip(*readers):
        frame, d = frames[0], frames[1][..., 0].astype(np.float32) / 255
        canvas = np.zeros((h, w, 3), np.float32)
        lum = frame[ys, xs].astype(np.float32).mean(axis=-1) / 255
        dd = d[ys, xs]
        rad = np.clip(1 + dd * near_boost * step / 6, 1, step / 2).astype(np.int32)
        val = np.clip(0.25 + 0.75 * lum, 0, 1) * (0.45 + 0.55 * dd)
        for r in np.unique(rad):
            sel = rad == r
            for x, y, v in zip(xs[sel], ys[sel], val[sel]):
                cv2.circle(canvas, (int(x), int(y)), int(r), (col * v * 255).tolist(), -1, lineType=cv2.LINE_AA)
        out = canvas
        if keep_person:
            m = frames[-1][..., :1].astype(np.float32) / 255
            out = frame.astype(np.float32) * m + canvas * (1 - m)
        wr.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
    wr.stdin.close(); wr.wait()
    return dst.name, n_pts
