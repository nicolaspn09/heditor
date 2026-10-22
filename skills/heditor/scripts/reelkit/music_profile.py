"""Profile of a music track for planning the edit: tempo, energy per second, kick entries, breakdowns and lifts.

Usage: music_profile.py <music:ID|track.mp3> [out.json]

Prints a compact report (and writes JSON when out.json is given). Use it to
pick the `src` of each music section so the track's own turns land on the speech turns: a kick entry or the end of a
breakdown on the strongest word, a breakdown under a suspense beat, a lift on the payoff. Measured, not listened:
say so when reporting.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

SR = 11025


def _pcm(path, af=None):
    args = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR)]
    if af:
        args += ["-af", af]
    raw = subprocess.run(args + ["-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def _db(x, hop):
    n = len(x) // hop
    return 20 * np.log10(np.sqrt(np.mean(x[: n * hop].reshape(n, hop).astype(np.float64) ** 2, axis=1)) + 1e-9)


def tempo(x):
    """Rough BPM (70-180) from the autocorrelation of the spectral flux in the first 60 s; strength 0-1."""
    h = 256
    fr = len(x) // h
    frames = x[: fr * h].reshape(fr, h) * np.hanning(h)
    spec = np.abs(np.fft.rfft(frames, axis=1))
    flux = np.maximum(np.diff(spec, axis=0), 0).sum(1)
    flux = flux - flux.mean()
    seg = flux[: int(60 * SR / h)]
    ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
    lags = np.arange(1, len(ac)) * h / SR
    bpm = 60 / lags
    ok = (bpm > 70) & (bpm < 180)
    i = int(np.argmax(ac[1:][ok]))
    return float(bpm[ok][i]), float(ac[1:][ok][i] / (ac[0] or 1))


def spans(mask, min_len):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            if j - i >= min_len:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def profile(path):
    x = _pcm(path)
    low = _pcm(path, "lowpass=f=120,lowpass=f=120")
    energy = _db(x, SR)                                     # dB per second
    low_share = _db(low, SR) - energy                       # how much of the energy is kick/bass, per second
    bpm, strength = tempo(x)
    kick = low_share > (np.median(low_share) - 6)
    breakdowns = [(a, b) for a, b in spans(~kick, 4)]       # >= 4 s without kick/bass
    entries = [b for a, b in breakdowns if b < len(kick)] + ([int(np.argmax(kick))] if not kick[0] else [])
    lifts = [i for i in range(2, len(energy)) if energy[i] - energy[i - 2] >= 5 and energy[i] > np.median(energy) - 3
             and not (energy[i - 1] - energy[i - 3 if i >= 3 else 0] >= 5)]
    return {"file": str(path), "duration_s": round(len(x) / SR, 2), "bpm": round(bpm, 1), "beat_s": round(60 / bpm, 3),
            "pulse_strength": round(strength, 2), "energy_db_per_s": [round(float(v), 1) for v in energy],
            "kick_per_s": [bool(v) for v in kick], "breakdowns_s": breakdowns, "kick_entries_s": sorted(set(entries)),
            "lifts_s": lifts}


def main():
    arg = sys.argv[1]
    if arg.startswith("music:"):
        import reelkit as rk
        arg = rk.music_path(arg)
    if not Path(arg).exists():
        sys.exit(f"music file not found: {arg} (catalog ids: assets/catalog.json; or pass a licensed file path)")
    prof = profile(arg)
    print(f"{Path(prof['file']).name}: {prof['duration_s']} s · ~{prof['bpm']} bpm (beat {prof['beat_s']} s, "
          f"pulse {prof['pulse_strength']})")
    print("energy dB/s:", " ".join(str(int(v)) for v in prof["energy_db_per_s"]))
    print("kick/bass  :", "".join("█" if k else "·" for k in prof["kick_per_s"]))
    print("breakdowns :", ", ".join(f"{a}-{b} s" for a, b in prof["breakdowns_s"]) or "none")
    print("kick enters:", ", ".join(f"{t} s" for t in prof["kick_entries_s"]) or "-")
    print("lifts (+5 dB in 2 s):", ", ".join(f"{t} s" for t in prof["lifts_s"]) or "-")
    print("Measured, not listened. Align a kick entry / breakdown end / lift with the strongest spoken word "
          "(section src = event_s - word_s).")
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(prof, indent=1))


if __name__ == "__main__":
    main()
