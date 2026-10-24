"""Finalize a cut: mux the master audio into the render, verify the MP4 and build a contact sheet.

Usage: finalize.py <work_dir> <final_name.mp4> <t1,t2,...|auto>
Writes <work>/render/<final_name>, <work>/qa/final-verification.json and qa/final-contact-sheet.jpg.
Checks: full decode, EBU R128 loudness and true peak (after AAC), audio correlation with master.wav,
freeze detection (advisory), top safe-margin by pixels, 40-frame contact sheet. The canvas, the safe top row and
the sheet cells follow the cut's format profile (plan.json "format", default 9:16). Long-form videos rendered in
segments use `heditor long finalize` instead.
"""

import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image

WORK, NAME = Path(sys.argv[1]).resolve(), sys.argv[2]
TIMES = None if sys.argv[3] == "auto" else [float(t) for t in sys.argv[3].split(",")]
SR = 48000
sys.path.insert(0, str(Path(__file__).parent))
import formats as fm  # noqa: E402
import reelkit as rk  # noqa: E402
BRAND = rk.load_brand(Path(sys.argv[1]))["name"]
FMT = fm.of_work(WORK)
SAFE_TOP = FMT.safe_top  # 270 for 9:16 Reels


def top_margin(video, duration, step=0.5):
    """First bright row (luma > 150 on more than 8 px) across frames sampled every `step` s; should be >= SAFE_TOP."""
    worst = 9999
    for t in np.arange(0.05, max(0.1, duration - 0.05), step):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-f", "rawvideo",
                              "-pix_fmt", "gray", "-"], capture_output=True).stdout
        if len(raw) != FMT.width * FMT.height:
            continue
        g = np.frombuffer(raw, np.uint8).reshape(FMT.height, FMT.width)
        rows = np.where((g > 150).sum(axis=1) > 8)[0]
        if len(rows):
            worst = min(worst, int(rows.min()))
    return worst


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, check=True, **kw)


def aac_true_peak(wav):
    """True peak of the master after AAC 256k encoding (AAC can overshoot the WAV peak)."""
    tmp = WORK / "render/tp-probe.m4a"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", "256k", "-ar", "48000", str(tmp)], timeout=300)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(tmp), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    tmp.unlink()
    peaks = [float(line.split()[1]) for line in out[out.rfind("Summary:"):].splitlines() if line.strip().startswith("Peak:")]
    return peaks[-1] if peaks else 0.0


def wav_lufs(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    vals = [float(line.split()[1]) for line in out[out.rfind("Summary:"):].splitlines() if line.strip().startswith("I:")]
    return vals[-1] if vals else None


def limit_peaks(src, dst, ceiling_db, gain_db=0.0):
    """Oversampled (4x) peak limiter with latency compensation: tames the transients without moving the audio."""
    af = (f"volume={gain_db:.3f}dB,aresample=192000,alimiter=limit={10 ** (ceiling_db / 20):.4f}:attack=1:release=60:"
          f"level=false:latency=1,aresample=48000")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(dst)],
        timeout=300)


def guard_true_peak(limit=-1.5, target_lufs=-14.0):
    """Bright transient SFX (beeps, clicks, shutters, stacked impacts) can push the AAC above 0 dBTP even with the WAV
    at -2 dB. If the post-AAC peak exceeds the limit, first limit only the peaks (oversampled limiter, gain kept so the
    loudness stays at the target); only if that fails, rebuild the master with a lower loudnorm TP (the loudness then
    drops ~1 dB, as a dynamic loudnorm with TP -4 does). The original is kept as master-pre-tp.wav."""
    master = WORK / "composition/assets/master.wav"
    tp = aac_true_peak(master)
    if tp <= limit:
        return {"aac_true_peak_before": tp}
    orig = WORK / "composition/assets/master-pre-tp.wav"
    if not orig.exists() or master.stat().st_mtime > orig.stat().st_mtime:   # a new produce wrote a new master
        orig.write_bytes(master.read_bytes())
    gain, lufs = 0.0, None
    for ceiling in (-3.0, -3.5, -4.0, -4.5, -5.0):
        for _ in range(3):
            limit_peaks(orig, master, ceiling, gain)
            lufs = wav_lufs(master)
            if lufs is None or abs(lufs - target_lufs) <= 0.1:
                break
            gain += target_lufs - lufs
        after = aac_true_peak(master)
        if after <= limit:
            return {"aac_true_peak_before": tp, "method": "limiter", "ceiling_db": ceiling, "gain_db": round(gain, 2),
                    "lufs_after": lufs, "aac_true_peak_after": after}
    for target in (-4.0, -5.0, -6.0):
        run(["ffmpeg", "-v", "error", "-y", "-i", str(orig), "-af", f"loudnorm=I=-14:TP={target}:LRA=9", "-ar", "48000",
             "-ac", "2", "-c:a", "pcm_s16le", str(master)], timeout=300)
        after = aac_true_peak(master)
        if after <= limit:
            return {"aac_true_peak_before": tp, "method": "loudnorm", "tp_target": target, "aac_true_peak_after": after}
    return {"aac_true_peak_before": tp, "aac_true_peak_after": after, "warning": "true peak above limit"}


def first_seconds(plan, seconds=15.0, thr_db=-45.0, bridge=0.25):
    """Hook metrics of the first `seconds`: share of time with voice (10 ms RMS of voice-raw.wav above `thr_db`,
    gaps shorter than `bridge` s bridged) and words started. Advisory for paid ads: proven hooks keep >= 90 % voice and
    >= 38 words in the first 15 s; dramatic pauses and slow cards belong after that."""
    voice = WORK / "composition/assets/voice-raw.wav"
    if not voice.exists():
        return None
    raw = subprocess.run(["ffmpeg", "-v", "error", "-t", str(seconds), "-i", str(voice), "-ac", "1", "-ar", str(SR), "-f",
                          "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    hop = SR // 100
    if len(x) < hop:
        return None
    on = 20 * np.log10(np.sqrt((x[: len(x) // hop * hop].reshape(-1, hop) ** 2).mean(1)) + 1e-12) > thr_db
    v, i = on.copy(), 0
    while i < len(on):
        if on[i]:
            i += 1
            continue
        j = i
        while j < len(on) and not on[j]:
            j += 1
        if 0 < i and j < len(on) and (j - i) * 0.01 < bridge:
            v[i:j] = True
        i = j
    words = sum(1 for c in plan.get("captions", []) for w in c.get("words", []) if w.get("start", 99) < seconds)
    return {"seconds": seconds, "voice_share": round(float(v.sum()) / (seconds * 100), 3), "words": words}


def main():
    render = WORK / "render/render.mp4"
    final = WORK / "render" / NAME
    plan = json.loads((WORK / "plan.json").read_text())
    tp_guard = guard_true_peak()
    # No `-shortest`: with `-c:v copy` it cuts the video at a packet boundary before the audio ends (2350 of
    # 2354 frames on a 78 s cut) and the contact sheet then asks for frames past the end. Trim to the render.
    vdur = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(render)]).stdout.strip()
    run(["ffmpeg", "-v", "error", "-y", "-i", str(render), "-i", str(WORK / "composition/assets/master.wav"),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
         "-movflags", "+faststart", "-metadata", f"artist={BRAND}", "-t", vdur, str(final)], timeout=300)
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"], capture_output=True, text=True)
    probe = json.loads(run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames,sample_rate,channels,pix_fmt",
                            "-of", "json", str(final)]).stdout)
    loud = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(final), "-af", "ebur128=peak=true", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    summ = loud[loud.rfind("Summary:"):]

    def grab(label):
        for line in summ.splitlines():
            if line.strip().startswith(label):
                return float(line.split()[1])
        return None

    a = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                     capture_output=True, check=True).stdout, np.float32)
    with wave.open(str(WORK / "composition/assets/master.wav")) as w:
        m = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2).mean(1) / 32768
    n = min(len(a), len(m))
    corr = float(np.corrcoef(a[:n], m[:n])[0, 1])
    # Freezes longer than 0.3 s (advisory: small cameras and intentional holds also trigger it)
    fz = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(final), "-vf", "freezedetect=n=-60dB:d=0.3",
                         "-map", "0:v", "-f", "null", "-"], capture_output=True, text=True).stderr
    freezes = [line.split("lavfi.freezedetect.")[1].strip() for line in fz.splitlines() if "freezedetect.freeze_" in line]
    times = TIMES or [round(0.03 + i * (plan["duration"] - 0.1) / 39, 2) for i in range(40)]
    frames_dir = WORK / "qa/final"
    frames_dir.mkdir(parents=True, exist_ok=True)
    shots = []
    for t in times:
        p = frames_dir / f"f-{t:06.2f}.png"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t}", "-i", str(final), "-frames:v", "1", str(p)])
        shots.append(p)
    cols = 6
    w_, h_ = FMT.thumb(width=270 if FMT.vertical else 224)
    sheet = Image.new("RGB", (cols * w_, ((len(shots) + cols - 1) // cols) * h_))
    for i, p in enumerate(shots):
        sheet.paste(Image.open(p).convert("RGB").resize((w_, h_)), ((i % cols) * w_, (i // cols) * h_))
    sheet.save(WORK / "qa/final-contact-sheet.jpg", quality=88)
    data = final.read_bytes()
    result = {
        "file": str(final), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "md5": hashlib.md5(data).hexdigest(),
        "decode_errors": decode.stderr.strip()[:500], "probe": probe, "lufs_i": grab("I:"), "lra": grab("LRA:"),
        "true_peak_dbfs": grab("Peak:"), "audio_master_corr": corr, "samples": n,
        "expected_duration": plan["duration"], "tp_guard": tp_guard, "first_15s": first_seconds(plan), "freezes": freezes, "top_margin_first_bright_row": top_margin(final, plan["duration"]), "safe_top": SAFE_TOP, "format": FMT.key, "contact_frames": len(times), "balance": json.loads((WORK / "qa/balance.json").read_text()),
    }
    (WORK / "qa/final-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ("probe",)}, ensure_ascii=False, indent=1))
    print(json.dumps(probe))
    if result["balance"].get("asr_check_required"):
        print(f"NEXT (required, mix profile {result['balance'].get('mix_profile')}): heditor asr-check {WORK}")


if __name__ == "__main__":
    main()
