"""ASR of the final mix versus the clean voice: checks that music and SFX do not mask the speech.

Usage: asr_check.py <work_dir>   (env HEDITOR_LANG, default "pt")
Target: master similarity >= 0.90 of the expected words and not more than 0.03 below the clean voice (exit 1 otherwise).\nLists MASKED spans (words the clean voice had and the mix lost) with times, to place local dips in the bed.\nMandatory gate for the "presence" mix profile.
"""

import difflib
import json
import os
import re
import sys
from pathlib import Path

from faster_whisper import WhisperModel

sys.path.insert(0, str(Path(__file__).parent))
from reelkit import load_audio_16k  # noqa: E402

WORK = Path(sys.argv[1])


def norm(text):
    return re.findall(r"[a-zà-ú0-9]+", text.lower())


def main():
    plan = json.loads((WORK / "plan.json").read_text())
    ref = norm(" ".join(w["word"] for c in plan["captions"] for w in c["words"]))
    model = WhisperModel(os.environ.get("HEDITOR_ASR_CHECK_MODEL", "small"), device="cpu", compute_type="int8", cpu_threads=2)
    out, timed = {}, {}
    for name in ["voice-master.wav", "master.wav"]:
        segs, _ = model.transcribe(load_audio_16k(WORK / "composition/assets" / name), language=os.environ.get("HEDITOR_LANG", "pt"),
                                   beam_size=5, vad_filter=False, word_timestamps=True)
        segs = [s for s in segs if s.start < plan["voice_end"]]
        rows = [{"start": s.start, "end": s.end, "text": s.text} for s in segs]
        timed[name] = [(t, w.start, w.end) for s in segs for w in (s.words or []) for t in norm(w.word)]
        heard = norm(" ".join(r["text"] for r in rows))
        out[name] = {"similarity": difflib.SequenceMatcher(None, ref, heard).ratio(), "text": " ".join(r["text"] for r in rows)}
    out["delta_master_minus_voice"] = out["master.wav"]["similarity"] - out["voice-master.wav"]["similarity"]
    # where the mix lost words the clean voice still had: candidates for a local dip in the bed (music section with
    # a lower gain_db over that phrase) or for moving an SFX into a gap
    v, m = timed["voice-master.wav"], timed["master.wav"]
    masked = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [x[0] for x in v], [x[0] for x in m]).get_opcodes():
        if op in ("replace", "delete") and i2 > i1:
            masked.append({"start": round(v[i1][1], 2), "end": round(v[i2 - 1][2], 2), "voice": " ".join(x[0] for x in v[i1:i2]),
                           "master": " ".join(x[0] for x in m[j1:j2])})
    out["masked_spans"] = masked
    out["pass"] = out["master.wav"]["similarity"] >= 0.90 and out["delta_master_minus_voice"] >= -0.03
    (WORK / "qa/asr-check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps({k: (v["similarity"] if isinstance(v, dict) else v) for k, v in out.items() if k != "masked_spans"}))
    print("MASTER:", out["master.wav"]["text"])
    for sp in masked:
        print(f"MASKED {sp['start']:6.2f}-{sp['end']:6.2f}  voice: {sp['voice']!r}  master: {sp['master']!r}")
    if not out["pass"]:
        print("FAIL: master similarity < 0.90 or more than 0.03 below the clean voice; dip the bed over the MASKED spans")
        sys.exit(1)


if __name__ == "__main__":
    main()
