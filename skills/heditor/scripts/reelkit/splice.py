"""Splice a new opening onto a video that is already delivered (hook tests on ads that already convert).

Usage:
  splice.py find-cut <video> <from_s> <to_s>
      Per-frame luma in the window: the first black frame after a lit one, the biggest picture jumps and whether the
      audio is silent there. The splice point is the index of that first black frame (or of the jump).
  splice.py <opening_work> <body.mp4> <out.mp4> [--cut-frame K] [--xfade-ms 8] [--no-match]
            [--overlay seal.png] [--overlay-until S] [--overlay-fade 0.30,0.25] [--crf 14]
      Output = the first round(D*fps) frames of <opening_work>/render/render.mp4 (D = plan.json duration) + the body
      from frame K to its end (K = 0 puts the opening before the whole body). Video is encoded once (H.264 High,
      yuv420p, bt709, faststart). Audio = the opening's composition/assets/master.wav (zero-padded to the exact frame
      length) + the body audio decoded whole without -ss and cut by sample, with an equal-power crossfade of
      `--xfade-ms` ending exactly on the cut (with K = 0 the opening tail fades out instead). The body audio is never
      processed. By default the opening gain is matched so its last 3 s have the loudness of the body's 3 s before the
      cut (or the first 3 s of the body when K < 3 s), capped at +-4 dB, and the opening alone is limited when its peak
      would pass -1.8 dBFS. `--overlay` draws a full-canvas transparent PNG (e.g. a campaign seal) over the body part
      from the splice until `--overlay-until` (output seconds), with fades.
      Writes <out>.splice.json: frame counts, gain, loudness (integrated, true peak, short-term 3 s centred on the
      splice versus the original cut), body audio correlation and lag against the delivered file, frame difference on
      sampled body frames, decode errors.

Why each detail (learnt on real hook tests):
- HyperFrames renders round(D*fps)+1 frames: using all of them adds a frame of silence and the bed stutters.
- `ffmpeg -ss 0` on an AAC file drops 1024 samples beyond the encoder priming: the body would come 21 ms early.
- `-shortest` cuts the last body frame: the frame count is set explicitly.
"""
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def probe(path):
    p = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_packets", "-of", "json", str(path)]).stdout)["streams"][0]
    num, den = (int(x) for x in p["r_frame_rate"].split("/"))
    return {"w": int(p["width"]), "h": int(p["height"]), "fps": num / den, "frames": int(p["nb_read_packets"])}


def decode_audio(path):
    """Whole file, stereo float at 48 kHz, no -ss (exact sample positions)."""
    out = run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]).stdout
    return np.frombuffer(out, np.float32).reshape(-1, 2).astype(np.float64)


def write_wav(path, x):
    y = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())


def ebur(path):
    """(integrated LUFS, true peak dBTP, [(t, S)] short-term 3 s series)."""
    r = subprocess.run(["ffmpeg", "-nostats", "-v", "verbose", "-i", str(path), "-af", "ebur128=peak=true:framelog=verbose",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    series = [(float(m.group(1)), float(m.group(2))) for m in
              (re.search(r"t:\s*([\d.]+).*?S:\s*(-?[\d.]+)\s", line) for line in r.splitlines()) if m]
    tail = r[r.rfind("Summary"):]
    i_lufs = float(re.search(r"I:\s*(-?[\d.]+) LUFS", tail).group(1))
    tp = re.search(r"Peak:\s*(-?[\d.]+|-inf) dBFS", tail.split("True peak:")[-1])
    return i_lufs, (float(tp.group(1)) if tp and tp.group(1) != "-inf" else -120.0), series


def loudness(x, tmp):
    write_wav(tmp, x)
    return ebur(tmp)


def s_at(series, t):
    vals = [p for p in series if p[1] > -100]
    return min(vals, key=lambda p: abs(p[0] - t))[1] if vals else None


def frame_lumas(video, t0, t1, fps):
    raw = run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", str(video), "-t", f"{t1 - t0:.3f}", "-vf",
               "scale=64:-2,format=gray", "-f", "rawvideo", "-"]).stdout
    p = probe(video)
    h = int(round(64 * p["h"] / p["w"] / 2) * 2)
    n = len(raw) // (64 * h)
    frames = np.frombuffer(raw[: n * 64 * h], np.uint8).reshape(n, h, 64).astype(np.float64)
    first = int(round(t0 * fps))
    return first, frames.mean(axis=(1, 2)), frames


def find_cut(video, t0, t1, black=12.0):
    p = probe(video)
    first, luma, frames = frame_lumas(video, t0, t1, p["fps"])
    blacks = [first + i for i in range(1, len(luma)) if luma[i] < black <= luma[i - 1]]
    jumps = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2)) if len(frames) > 1 else np.array([])
    top = sorted(range(len(jumps)), key=lambda i: -jumps[i])[:5]
    audio = decode_audio(video)
    rep = {"video": str(video), "fps": p["fps"], "frames": p["frames"],
           "first_black_frames": [{"frame": k, "t": round(k / p["fps"], 4), "luma_before": round(float(luma[k - first - 1]), 1),
                                   "luma": round(float(luma[k - first]), 1)} for k in blacks],
           "picture_jumps": [{"frame": first + i + 1, "t": round((first + i + 1) / p["fps"], 4),
                              "mean_abs_diff": round(float(jumps[i]), 1)} for i in sorted(top)]}
    for item in rep["first_black_frames"] + rep["picture_jumps"]:
        s = int(item["t"] * SR)
        win = audio[max(0, s - int(0.05 * SR)): s + int(0.05 * SR)]
        item["audio_rms_db_100ms"] = round(float(20 * np.log10(np.sqrt((win ** 2).mean()) + 1e-12)), 1) if len(win) else None
    return rep


def _opt(args, name, default=None, cast=str):
    if name in args:
        i = args.index(name)
        val = args[i + 1]
        del args[i:i + 2]
        return cast(val)
    return default


def splice(opening, body, out, cut_frame=0, xfade_ms=8.0, match=True, overlay=None, overlay_until=None,
           overlay_fade=(0.30, 0.25), crf=14):
    opening, body, out = Path(opening), Path(body), Path(out)
    plan = json.loads((opening / "plan.json").read_text())
    pb = probe(body)
    fps = pb["fps"]
    po = probe(opening / "render/render.mp4")
    assert (po["w"], po["h"]) == (pb["w"], pb["h"]), f"canvas differs: opening {po['w']}x{po['h']}, body {pb['w']}x{pb['h']}"
    n_open = int(round(plan["duration"] * fps))
    assert po["frames"] >= n_open, f"opening render has {po['frames']} frames, needs {n_open}"
    k = int(cut_frame)
    tmp = out.parent / f".{out.stem}.splice"
    tmp.mkdir(parents=True, exist_ok=True)
    # ---------------- audio
    b = decode_audio(body)
    i_cut = int(round(k / fps * SR))
    n_o = int(round(n_open / fps * SR))
    o = decode_audio(opening / "composition/assets/master.wav")[:n_o]
    if len(o) < n_o:
        o = np.concatenate([o, np.zeros((n_o - len(o), 2))])
    gain_db, ref_lufs, open_lufs = 0.0, None, None
    if match:
        ref = b[max(0, i_cut - 3 * SR): i_cut] if i_cut >= 3 * SR else b[: 3 * SR]
        ref_lufs, _, _ = loudness(ref, tmp / "ref.wav")
        open_lufs, _, _ = loudness(o[-3 * SR:], tmp / "open3.wav")
        if ref_lufs > -70 and open_lufs > -70:
            gain_db = float(np.clip(ref_lufs - open_lufs, -4.0, 4.0))
    o = o * 10 ** (gain_db / 20)
    limited = False
    if np.abs(o).max() > 10 ** (-1.8 / 20):
        write_wav(tmp / "open.wav", o)
        lim = 10 ** (-2.5 / 20)
        run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp / "open.wav"), "-af",
             f"aresample=192000,alimiter=limit={lim:.4f}:attack=1:release=60:level=false:latency=1,aresample={SR}",
             "-ac", "2", "-c:a", "pcm_s16le", str(tmp / "open_lim.wav")])
        o = decode_audio(tmp / "open_lim.wav")[:n_o]
        if len(o) < n_o:
            o = np.concatenate([o, np.zeros((n_o - len(o), 2))])
        limited = True
    nxf = max(1, int(round(xfade_ms / 1000 * SR)))
    w_out = (np.cos(np.linspace(0, np.pi / 2, nxf)) ** 2)[:, None]
    o_x = o.copy()
    if i_cut >= nxf:
        o_x[-nxf:] = o[-nxf:] * w_out + b[i_cut - nxf: i_cut] * (1 - w_out)
    else:
        o_x[-nxf:] = o[-nxf:] * w_out
    final_audio = np.concatenate([o_x, b[i_cut:]])
    write_wav(tmp / "audio.wav", final_audio)
    # ---------------- video
    body_frames = pb["frames"] - k
    body_dur = body_frames / fps
    graph = (f"[0:v]trim=end_frame={n_open},setpts=PTS-STARTPTS,format=yuv420p[o];"
             f"[1:v]trim=start_frame={k},setpts=PTS-STARTPTS,format=yuv420p[b];")
    inputs = ["-i", str(opening / "render/render.mp4"), "-i", str(body)]
    if overlay:
        until = (overlay_until - n_open / fps) if overlay_until is not None else body_dur
        until = max(0.1, min(until, body_dur))
        fi, fo = overlay_fade
        inputs += ["-loop", "1", "-framerate", f"{fps:g}", "-i", str(overlay)]
        graph += (f"[2:v]format=rgba,trim=duration={body_dur:.4f},setpts=PTS-STARTPTS,"
                  f"fade=t=in:st=0:d={fi}:alpha=1,fade=t=out:st={max(0.0, until - fo):.4f}:d={fo}:alpha=1[s];"
                  f"[b][s]overlay=0:0:format=auto:enable='between(t,0,{until:.4f})',format=yuv420p[bs];"
                  f"[o][bs]concat=n=2:v=1:a=0,setsar=1,format=yuv420p[v]")
        audio_idx = 3
    else:
        graph += "[o][b]concat=n=2:v=1:a=0,setsar=1,format=yuv420p[v]"
        audio_idx = 2
    inputs += ["-i", str(tmp / "audio.wav")]
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-map", f"{audio_idx}:a",
         "-r", f"{fps:g}", "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
         "-c:a", "aac", "-b:a", "256k", "-ar", str(SR), "-movflags", "+faststart",
         "-frames:v", str(n_open + body_frames), str(out)])
    rep = verify(out, body, n_open, k, fps, nxf, gain_db, limited, ref_lufs, open_lufs, overlay is not None)
    rep["opening_audio"] = _align(o_x[: max(0, n_o - nxf)], decode_audio(out)[: max(0, n_o - nxf)])
    rep["ok"] = rep["ok"] and rep["opening_audio"]["lag_samples"] == 0
    Path(str(out) + ".splice.json").write_text(json.dumps(rep, indent=1))
    return rep


def _align(ref, got, max_lag=96):
    """Correlation and lag of the encoded opening against the audio that was written (catches filter latency)."""
    n = min(len(ref), len(got)) - 2 * max_lag
    if n < SR // 2:
        return {"correlation": None, "lag_samples": 0}
    x = ref[max_lag: max_lag + n, 0]
    best = (0.0, 0)
    for lg in range(-max_lag, max_lag + 1):
        y = got[max_lag + lg: max_lag + lg + n, 0]
        if x.std() > 0 and y.std() > 0:
            c = float(np.corrcoef(x, y)[0, 1])
            best = max(best, (c, lg))
    return {"correlation": round(best[0], 5), "lag_samples": best[1]}


def verify(out, body, n_open, k, fps, nxf, gain_db, limited, ref_lufs, open_lufs, has_overlay):
    po = probe(out)
    i_lufs, tp, series = ebur(out)
    _, _, series_b = ebur(body)
    splice_t = n_open / fps
    # body audio identical: compare the output after the crossfade with the delivered file, lag search +-64 samples
    a_out, a_body = decode_audio(out), decode_audio(body)
    s0 = int(round(splice_t * SR)) + nxf + SR // 10
    b0 = int(round(k / fps * SR)) + nxf + SR // 10
    n = min(len(a_out) - s0, len(a_body) - b0, 20 * SR) - 128
    corr, lag = 0.0, 0
    if n > SR:
        x = a_body[b0 + 64: b0 + 64 + n, 0]
        for lg in range(-64, 65):
            y = a_out[s0 + 64 + lg: s0 + 64 + lg + n, 0]
            c = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else 0.0
            if c > corr:
                corr, lag = c, lg
    # picture: mean abs difference on a few body frames (higher where the overlay sits)
    diffs = []
    pb = probe(body)
    for frac in (0.2, 0.5, 0.85):
        fb = k + int((pb["frames"] - k) * frac)
        fo = n_open + (fb - k)
        ga = run(["ffmpeg", "-v", "error", "-i", str(body), "-vf", f"select=eq(n\\,{fb}),scale=270:-2,format=gray",
                  "-frames:v", "1", "-f", "rawvideo", "-"]).stdout
        gb = run(["ffmpeg", "-v", "error", "-i", str(out), "-vf", f"select=eq(n\\,{fo}),scale=270:-2,format=gray",
                  "-frames:v", "1", "-f", "rawvideo", "-"]).stdout
        if ga and len(ga) == len(gb):
            diffs.append(round(float(np.abs(np.frombuffer(ga, np.uint8).astype(int) - np.frombuffer(gb, np.uint8)).mean()), 2))
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-f", "null", "-"], capture_output=True, text=True)
    rep = {"file": str(out), "frames": po["frames"], "expected_frames": n_open + pb["frames"] - k, "fps": fps,
           "opening_frames": n_open, "splice_s": round(splice_t, 4), "body_cut_frame": k, "body_cut_s": round(k / fps, 4),
           "opening_gain_db": round(gain_db, 2), "opening_limited": limited,
           "loudness_match": {"body_ref_lufs": ref_lufs, "opening_last3s_lufs_before_gain": open_lufs},
           "lufs_i": i_lufs, "true_peak_dbtp": tp,
           "short_term_3s_centred": {"new": s_at(series, splice_t + 1.5), "original": s_at(series_b, k / fps + 1.5)},
           "body_audio": {"correlation": round(corr, 5), "lag_samples": lag},
           "body_frame_mean_abs_diff": diffs, "overlay": has_overlay, "decode_errors": dec.stderr.strip()}
    rep["ok"] = (rep["frames"] == rep["expected_frames"] and corr >= 0.999 and lag == 0 and not rep["decode_errors"]
                 and tp <= -1.5)
    Path(str(out) + ".splice.json").write_text(json.dumps(rep, indent=1))
    return rep


def main(argv):
    if argv[:1] == ["find-cut"] and len(argv) == 4:
        print(json.dumps(find_cut(Path(argv[1]), float(argv[2]), float(argv[3])), indent=1))
        return
    args = list(argv)
    cut = _opt(args, "--cut-frame", 0, int)
    xf = _opt(args, "--xfade-ms", 8.0, float)
    overlay = _opt(args, "--overlay")
    until = _opt(args, "--overlay-until", None, float)
    fade = _opt(args, "--overlay-fade", "0.30,0.25")
    crf = _opt(args, "--crf", 14, int)
    match = "--no-match" not in args
    args = [a for a in args if a != "--no-match"]
    if len(args) != 3:
        sys.exit(__doc__)
    rep = splice(args[0], args[1], args[2], cut, xf, match, overlay, until, tuple(float(x) for x in fade.split(",")), crf)
    print(json.dumps(rep, indent=1))
    if not rep["ok"]:
        print("CHECK: frame count, body audio correlation/lag, true peak or decode errors did not pass")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
