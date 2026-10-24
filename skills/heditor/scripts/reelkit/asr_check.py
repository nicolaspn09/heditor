"""ASR of the final mix versus the clean voice: checks that music and SFX do not mask the speech.

Usage: asr_check.py <work_dir>   (env HEDITOR_LANG, default "pt")
Target: master similarity >= 0.90 of the expected words and not more than 0.03 below the clean voice (exit 1 otherwise).
Similarity is measured on notation-folded tokens (textnorm: "pra"/"para", "7h30"/"sete e meia", "5"/"cinco",
"IA Builders"/"IABuilders"), because ASR writes the same spoken words in different notations and that is not masking;
the raw (unfolded) values are reported too. HEDITOR_ASR_CHECK_STRICT=1 gates on the raw values.
Lists MASKED spans (words the clean voice had and the mix lost) with times, to place local dips in the bed;
notation-only differences are listed apart as NOTATION and never need a dip.
Mandatory gate for the "presence" mix profile.
"""

import difflib
import json
import os
import sys
from pathlib import Path

from faster_whisper import WhisperModel

sys.path.insert(0, str(Path(__file__).parent))
from reelkit import load_audio_16k  # noqa: E402
from textnorm import notation_tokens, same_notation, tokens  # noqa: E402

WORK = Path(sys.argv[1])
LANG = os.environ.get("HEDITOR_LANG", "pt")


def ratio(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def main():
    plan = json.loads((WORK / "plan.json").read_text())
    ref_text = " ".join(w["word"] for c in plan["captions"] for w in c["words"])
    model = WhisperModel(os.environ.get("HEDITOR_ASR_CHECK_MODEL", "small"), device="cpu", compute_type="int8", cpu_threads=2)
    out, timed = {}, {}
    for name in ["voice-master.wav", "master.wav"]:
        segs, _ = model.transcribe(load_audio_16k(WORK / "composition/assets" / name), language=LANG,
                                   beam_size=5, vad_filter=False, word_timestamps=True)
        segs = [s for s in segs if s.start < plan["voice_end"]]
        text = " ".join(s.text for s in segs)
        timed[name] = [(t, w.start, w.end) for s in segs for w in (s.words or []) for t in tokens(w.word)]
        out[name] = {"similarity": ratio(notation_tokens(ref_text, LANG), notation_tokens(text, LANG)),
                     "similarity_raw": ratio(tokens(ref_text), tokens(text)), "text": text}
    v_sim, m_sim = out["voice-master.wav"], out["master.wav"]
    out["delta_master_minus_voice"] = m_sim["similarity"] - v_sim["similarity"]
    out["delta_raw"] = m_sim["similarity_raw"] - v_sim["similarity_raw"]
    # where the mix lost words the clean voice still had: candidates for a local dip in the bed (music section with
    # a lower gain_db over that phrase) or for moving an SFX into a gap
    v, m = timed["voice-master.wav"], timed["master.wav"]
    masked, notation = [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [x[0] for x in v], [x[0] for x in m]).get_opcodes():
        if op in ("replace", "delete") and i2 > i1:
            span = {"start": round(v[i1][1], 2), "end": round(v[i2 - 1][2], 2), "voice": " ".join(x[0] for x in v[i1:i2]),
                    "master": " ".join(x[0] for x in m[j1:j2])}
            (notation if same_notation(span["voice"], span["master"], LANG) else masked).append(span)
    out["masked_spans"], out["notation_spans"] = masked, notation
    strict = os.environ.get("HEDITOR_ASR_CHECK_STRICT") == "1"
    sim, delta = (m_sim["similarity_raw"], out["delta_raw"]) if strict else (m_sim["similarity"], out["delta_master_minus_voice"])
    out["gate"] = "raw" if strict else "notation-folded"
    out["pass"] = sim >= 0.90 and delta >= -0.03
    (WORK / "qa/asr-check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps({"voice-master.wav": v_sim["similarity"], "master.wav": m_sim["similarity"],
                      "delta_master_minus_voice": out["delta_master_minus_voice"],
                      "raw": {"voice": v_sim["similarity_raw"], "master": m_sim["similarity_raw"]},
                      "gate": out["gate"], "pass": out["pass"]}))
    print("MASTER:", m_sim["text"])
    for sp in masked:
        print(f"MASKED {sp['start']:6.2f}-{sp['end']:6.2f}  voice: {sp['voice']!r}  master: {sp['master']!r}")
    for sp in notation:
        print(f"NOTATION {sp['start']:6.2f}-{sp['end']:6.2f}  voice: {sp['voice']!r}  master: {sp['master']!r}")
    if not out["pass"]:
        print("FAIL: master similarity < 0.90 or more than 0.03 below the clean voice; dip the bed over the MASKED spans "
              "(check each one with a short large-v3 window on both files before changing the mix)")
        sys.exit(1)


if __name__ == "__main__":
    main()
