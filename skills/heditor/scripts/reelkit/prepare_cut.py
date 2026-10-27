"""Prepare the speech and camera of a cut from the source recording.

Usage inside a cut's prepare.py:
    from prepare_cut import prepare_cut
    prepare_cut(SOURCE, WORK, BLOCKS, crop="crop=320:238:1548:412")   # or crop=None for the full frame

BLOCKS: list of (key, start, end, end_radius[, start_radius]) in seconds of the source. Boundaries snap to the
energy valley (10 ms windows) and to whole frames. The silence threshold is measured per recording:
noise floor (10th percentile of 10 ms RMS) + 12 dB, clamped to [-48, -32] dBFS. Speed is always 1x (never
speed up speech).

Dead air is removed in two places, because both read as "the editor forgot to cut the pause":
- inside a block, pauses longer than `min_pause` are shortened, keeping `edge` seconds on each side;
- at the edges of every block, silence before the first voiced 10 ms window is trimmed to `lead` seconds and
  silence after the last voiced window to `tail` seconds. Block junctions therefore leave ~lead + tail of air,
  never the whole snapping radius on both sides (the v1 failure: 0.8-1.3 s gaps at every junction).
Pass lead=None / tail=None to keep the old snap-only behaviour. `heditor gaps <work>` lists what is left.
Outputs: composition/assets/camera-src.mp4, voice-raw.wav and edl.json.

Format profiles: `fmt` (default "9:16") is recorded in edl.json; crop="fit:<fmt>" (e.g. "fit:9:16", "fit:1:1")
computes a centred crop of the source that fills that profile's aspect (formats.crop_for). For screen-share
recordings and long videos use `heditor long` instead (references/long-form.md).
"""

import json
import math
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000


def _pcm(source, start, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.4f}", "-t", f"{dur:.4f}", "-i", str(source),
                          "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def _rms10(x):
    hop = SR // 100
    f = x[: len(x) // hop * hop].reshape(-1, hop)
    return 20 * np.log10(np.sqrt(np.mean(f ** 2, axis=1)) + 1e-9)


def _quiet(source, t, radius):
    r = _rms10(_pcm(source, t - radius, 2 * radius))
    i = int(np.argmin(r))
    return t - radius + (i + 0.5) / 100, float(r[i])


def _voiced_span(quiet, min_run=4):
    """First/last 10 ms window of speech, ignoring voiced blips shorter than `min_run` windows (clicks)."""
    first = last = None
    i = 0
    while i < len(quiet):
        if not quiet[i]:
            j = i
            while j < len(quiet) and not quiet[j]:
                j += 1
            if j - i >= min_run:
                first = i if first is None else first
                last = j
            i = j
        else:
            i += 1
    return first, last


def cut_on_seam(r0, r1, s, e, start, fps, seams):
    """Shift a pause trim so its cut lands on a scene seam inside the pause, removing the same number of frames.

    Sources joined from scenes (AI avatar studio videos, spliced takes) reset the pose at every seam. When the seam
    sits in a kept edge of the pause, the trim cut and the pose reset become two jumps a few frames apart (a stutter
    that edits tend to hide by blanking the speaker). Moving the removed window so the joint is "last frame of the old
    scene -> first frame of the new one" leaves a single discontinuity, at the seam, and keeps the timeline intact.

    r0/r1: removed frames [r0, r1) relative to the block start; s/e: the pause in seconds relative to the block start;
    start: block start in source seconds; seams: source times of the first frame of each new scene.
    Returns (r0, r1, seam or None).
    """
    tol = 1.0 / fps
    for t in seams or ():
        rel = t - start
        if not (s - tol <= rel <= e + tol):
            continue
        ft = round(rel * fps)
        if r0 <= ft <= r1:
            return r0, r1, t
        width = r1 - r0
        if ft > r1:
            return ft - width, ft, t
        return ft, ft + width, t
    return r0, r1, None


def prepare_cut(source, work, blocks, crop, fps=24, min_pause=0.35, edge=0.12, tail_fade=0.04,
                lead=0.08, tail=0.12, fmt=None, seams=None):
    source, work = Path(source), Path(work)
    if crop and str(crop).startswith("fit:"):
        import formats
        size = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                               "-of", "csv=p=0", str(source)], capture_output=True, text=True, check=True).stdout.strip()
        sw, sh = map(int, size.split(",")[:2])
        fmt = fmt or crop[4:]
        crop = formats.crop_for(sw, sh, crop[4:])
    assets = work / "composition/assets"
    assets.mkdir(parents=True, exist_ok=True)
    (work / "clips").mkdir(exist_ok=True)
    (work / "qa").mkdir(exist_ok=True)
    # ("PAUSE", seconds[, key]) inserts digital silence + black frames (style trailer: dramatic beats for
    # title cards and hits). Pauses are listed in edl["pauses"]; gaps/tests count only the silence around them.
    blocks = [tuple(bl) if str(bl[0]).upper() == "PAUSE" else tuple(bl) + (0.2,) * (5 - len(bl)) for bl in blocks]
    speech = [bl for bl in blocks if str(bl[0]).upper() != "PAUSE"]
    levels = np.concatenate([_rms10(_pcm(source, bl[1], bl[2] - bl[1])) for bl in speech])
    floor = float(np.percentile(levels, 10))
    thr = min(-32.0, max(-48.0, floor + 12))
    voice, videos, chunks, trims, pauses, cursor = [], [], [], [], [], 0.0
    for g, block in enumerate(blocks):
        if str(block[0]).upper() == "PAUSE":
            frames = max(1, round(float(block[1]) * fps))
            key = block[2] if len(block) > 2 else f"pause-{g}"
            span = frames / fps
            voice.append(np.zeros(frames * SR // fps))
            pauses.append({"key": key, "out_start": cursor, "out_end": cursor + span})
            chunks.append({"block": key, "pause": True, "source_in": None, "source_out": None,
                           "out_start": cursor, "out_end": cursor + span, "speed": 1.0})
            cursor += span
            videos.append(("PAUSE", g, frames))
            continue
        key, a, b, rb, ra = block
        qa_, da = _quiet(source, a, ra)
        qb_, db_ = _quiet(source, b, rb)
        f0, f1 = round(qa_ * fps), math.floor(qb_ * fps + 1e-6)
        start, dur = f0 / fps, (f1 - f0) / fps
        x = _pcm(source, start, dur)
        n = round(dur * SR)
        x = np.pad(x[:n], (0, max(0, n - len(x))))
        lv = _rms10(x)
        quiet = lv < thr
        removed, i = [], 0
        while i < len(quiet):
            if quiet[i]:
                j = i
                while j < len(quiet) and quiet[j]:
                    j += 1
                s, e = i / 100, j / 100
                if e - s > min_pause and s > 0.1 and e < dur - 0.1:
                    r0, r1 = math.ceil((s + edge) * fps - 1e-6), math.floor((e - edge) * fps + 1e-6)
                    if r1 - r0 >= 1:
                        r0, r1, seam = cut_on_seam(r0, r1, s, e, start, fps, seams)
                        removed.append((r0, r1))
                        trims.append({"block": key, "source_start": start + s, "source_end": start + e,
                                      "removed_s": (r1 - r0) / fps,
                                      **({"seam": seam, "cut_source": start + r1 / fps} if seam is not None else {})})
                i = j
            else:
                i += 1
        lo, hi = 0, f1 - f0
        first, last = _voiced_span(quiet)
        if first is not None and last is not None:
            if lead is not None:
                lo = max(0, math.floor((first / 100 - lead) * fps))
            if tail is not None:
                hi = min(f1 - f0, math.ceil((last / 100 + tail) * fps))
        keeps, pos = [], lo
        for r0, r1 in removed:
            r0, r1 = max(r0, lo), min(r1, hi)
            if r1 <= pos or r0 >= hi:
                continue
            if r0 > pos:
                keeps.append((pos, r0))
            pos = max(pos, r1)
        if hi > pos:
            keeps.append((pos, hi))
        graph = ""
        for k, (k0, k1) in enumerate(keeps):
            seg = x[k0 * SR // fps: k1 * SR // fps].copy()
            r = round(0.004 * SR)
            seg[:r] *= np.linspace(0, 1, r)
            seg[-r:] *= np.linspace(1, 0, r)
            voice.append(seg)
            span = (k1 - k0) / fps
            chunks.append({"block": key, "source_in": start + k0 / fps, "source_out": start + k1 / fps,
                           "out_start": cursor, "out_end": cursor + span, "speed": 1.0})
            cursor += span
            graph += f"[0:v]trim=start_frame={k0}:end_frame={k1},setpts=PTS-STARTPTS[v{k}];"
        chunks[-1]["boundary_db"] = [round(da, 1), round(db_, 1)]
        graph += "".join(f"[v{k}]" for k in range(len(keeps))) + f"concat=n={len(keeps)}:v=1:a=0,format=yuv420p[v]"
        raw_clip, clip = work / "clips" / f"raw-{g}.mp4", work / "clips" / f"edited-{g}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.4f}", "-i", str(source), *(["-vf", crop] if crop else []), "-an",
                        "-frames:v", str(f1 - f0), "-r", str(fps), "-c:v", "libx264", "-crf", "14", "-preset", "fast",
                        str(raw_clip)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw_clip), "-filter_complex", graph, "-map", "[v]", "-an",
                        "-r", str(fps), "-c:v", "libx264", "-crf", "14", "-preset", "fast", str(clip)], check=True)
        videos.append(clip)
    real = [v for v in videos if not isinstance(v, tuple)]
    if len(real) < len(videos):
        size = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                               "-of", "csv=p=0", str(real[0])], capture_output=True, text=True, check=True).stdout.strip()
        vw, vh = map(int, size.split(",")[:2])
        for i, v in enumerate(videos):
            if isinstance(v, tuple):
                clip = work / "clips" / f"pause-{v[1]}.mp4"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={vw}x{vh}:r={fps}",
                                "-frames:v", str(v[2]), "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "14",
                                "-preset", "fast", str(clip)], check=True)
                videos[i] = clip
    lst = work / "clips/list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in videos))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(assets / "camera-src.mp4")], check=True)
    v = np.concatenate(voice)
    t = round(tail_fade * SR)
    v[-t:] *= np.linspace(1, 0, t)
    peak = float(np.max(np.abs(v)))
    if peak > 0.98:
        v *= 0.98 / peak
    with wave.open(str(assets / "voice-raw.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((v * 32767).astype("<i2").tobytes())
    edl = {"source": str(source), "format": fmt or "9:16", "fps": fps, "crop": crop, "speed": 1.0, "voice_duration": len(v) / SR,
           "noise_floor_dbfs": round(floor, 1), "silence_threshold_dbfs": round(thr, 1), "min_pause_s": min_pause,
           "pause_edge_s": edge, "lead_s": lead, "tail_s": tail,
           "chunks": chunks, "pauses": pauses, "silence_trims": trims,
           "removed_seconds": sum(x["removed_s"] for x in trims)}
    (work / "edl.json").write_text(json.dumps(edl, ensure_ascii=False, indent=2))
    return edl
