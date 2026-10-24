"""Triage of raw takes: split a recording at silence, transcribe every chunk alone and flag what must not be used.

Usage: triage.py <video> [<video> ...] [--out DIR] [--model large-v3] [--lang pt] [--thr -55] [--gap 0.30]
Writes DIR/<stem>.triage.json and DIR/<stem>.triage.md (default DIR: ./triage) and prints the table.

Why: scripted recordings (teleprompter reading, ad scripts) come with reading pauses between sentences, false starts,
sentences said twice and asides to the editor ("cut that", "again", "corta aí, editor", "vou falar de novo").
Transcribing the whole file hides them: Whisper glues silences into words and invents repetitions ("WhatsApp.
WhatsApp."). Here every chunk between silences (10 ms RMS under `thr` dBFS for at least `gap` s) is transcribed alone,
then labelled:

- keep         usable speech;
- retake       superseded by a later take of the same sentence (same opening words or similar text), or the take
               right before an aside to the editor (the speaker rejected it);
- false_start  a short chunk that the next chunk restarts;
- editor       an aside to the editor or the crew (strong cue anywhere, weak cue in a short chunk);
- noise        breath/click/lip noise read as a word, very short chunks.

The labels are proposals for the human/agent review: read every `retake`/`editor` line before cutting, keep the best
take of each sentence and never splice half-sentences.
"""
import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from textnorm import notation_tokens  # noqa: E402

SR = 16000
STRONG = {
    "pt": ["corta ai", "corta isso", "corta essa", "vamos de novo", "vou de novo", "de novo agora", "vou repetir",
           "vou falar de novo", "vou falar a frase de novo", "deixa eu repetir", "deixa eu falar de novo", "foi errado",
           "vamos editar", "errei", "esquece isso", "esquece essa", "nao vale", "pode cortar", "volta ai"],
    "en": ["cut that", "cut this", "let me redo", "let me do that again", "one more time", "scratch that", "take two",
           "from the top", "i messed up", "start over"],
}
WEAK = {
    "pt": ["nao", "editor", "de novo", "atencao", "pera", "espera", "agora nao", "repete", "obrigado", "valeu", "tchau",
           "ops", "opa", "droga"],
    "en": ["no", "editor", "again", "wait", "sorry", "thanks", "thank you", "oops", "hold on"],
}
WEAK_MAX_WORDS = 6
# Whisper's stock hallucinations on breaths, clicks and room tone (subtitle credits, channel outros)
HALLUCINATIONS = ["legendas pela comunidade", "amara org", "inscreva se no canal", "obrigado por assistir",
                  "subtitles by", "thanks for watching", "transcribed by"]


def _plain(text, lang):
    """Tokens without accents for cue matching ("não" -> "nao", "aí" -> "ai")."""
    tr = str.maketrans("áàâãéêíóôõúüç", "aaaaeeiooouuc")
    return [t.translate(tr) for t in notation_tokens(text, lang)]


def _has(seq, cue):
    return any(seq[i:i + len(cue)] == cue for i in range(len(seq) - len(cue) + 1))


def is_editor(text, lang="pt"):
    """Strong cue anywhere, or a short chunk (<= WEAK_MAX_WORDS tokens) that starts with a weak cue."""
    toks = _plain(text, lang)
    if any(_has(toks, _plain(c, lang)) for c in STRONG.get(lang, [])):
        return True
    return len(toks) <= WEAK_MAX_WORDS and any(toks[:len(cue)] == cue for cue in (_plain(c, lang) for c in WEAK.get(lang, [])))


def voiced_chunks(db, win=0.01, thr=-55.0, gap=0.30, min_len=0.08):
    """Runs of windows above `thr` dB, merged across gaps shorter than `gap` s -> [[start_s, end_s], ...]."""
    spans, start = [], None
    for i, on in enumerate(np.asarray(db) > thr):
        if on and start is None:
            start = i
        elif not on and start is not None:
            spans.append([start * win, i * win])
            start = None
    if start is not None:
        spans.append([start * win, len(db) * win])
    merged = []
    for s in spans:
        if merged and s[0] - merged[-1][1] < gap:
            merged[-1][1] = s[1]
        else:
            merged.append(list(s))
    return [[round(a, 2), round(b, 2)] for a, b in merged if b - a >= min_len]


def _similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def classify(chunks, lang="pt", lookahead=4):
    """Label chunks in place (see module doc). `chunks`: [{"a", "b", "text", "words": [{"p"...}]}] in time order."""
    toks = [notation_tokens(c["text"], lang) for c in chunks]
    for c, t in zip(chunks, toks):
        c["label"], c["note"] = "keep", ""
        probs = [w.get("p", 1.0) for w in c.get("words", [])]
        dur = max(0.01, c["b"] - c["a"])
        if not t or (dur < 0.35 and len(t) <= 1) or (len(t) <= 2 and probs and max(probs) < 0.5):
            c["label"], c["note"] = "noise", "too short or low-confidence"
        elif (dur < 1.0 and len(t) / dur > 8) or any(_has(_plain(c["text"], lang), _plain(h, lang)) for h in HALLUCINATIONS):
            c["label"], c["note"] = "noise", "ASR hallucination on a noise chunk"
        elif is_editor(c["text"], lang):
            c["label"], c["note"] = "editor", "aside to the editor/crew"
    for i, c in enumerate(chunks):
        if c["label"] != "keep":
            continue
        nxt = next((k for k in range(i + 1, len(chunks)) if chunks[k]["label"] != "noise"), None)
        prv = next((k for k in range(i - 1, -1, -1) if chunks[k]["label"] != "noise"), None)
        ti = toks[i]
        if nxt is not None and chunks[nxt]["label"] == "editor":
            c["label"], c["note"] = "retake", f"followed by an aside to the editor (#{nxt}): probably rejected"
            continue
        if (nxt is not None and ti and toks[nxt] and ti[0] == toks[nxt][0] and len(toks[nxt]) > len(ti)
                and (len(ti) <= 2 or (len(ti) <= 3 and c["text"].rstrip().endswith(("...", "…"))))):
            c["label"], c["note"] = "false_start", f"restarted by #{nxt}"
            continue
        for j in range(i + 1, min(len(chunks), i + 1 + lookahead)):
            d = chunks[j]
            if d["label"] in ("noise", "editor"):
                continue
            tj = toks[j]
            same_start = len(ti) >= 3 and len(tj) >= 3 and ti[:3] == tj[:3]
            if same_start or (len(ti) >= 4 and _similar(ti, tj) >= 0.6):
                lab = "false_start" if len(ti) < 0.6 * len(tj) else "retake"
                c["label"], c["note"] = lab, f"superseded by #{j}"
                break
        if c["label"] == "keep" and prv is not None and chunks[prv]["label"] == "editor":
            c["note"] = f"right after an aside (#{prv}): confirm it is speech for the cut"
    return chunks


def _load(path):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)


def _db(audio, win=0.01):
    n = int(SR * win)
    frames = len(audio) // n
    return 20 * np.log10(np.sqrt(np.mean(audio[: frames * n].reshape(frames, n) ** 2, axis=1)) + 1e-12)


def triage(path, model, lang="pt", thr=-55.0, gap=0.30):
    audio = _load(path)
    rows = []
    for a, b in voiced_chunks(_db(audio), thr=thr, gap=gap):
        pa, pb = max(0.0, a - 0.15), min(len(audio) / SR, b + 0.15)
        segs, _ = model.transcribe(audio[int(pa * SR): int(pb * SR)], language=lang, beam_size=5, word_timestamps=True,
                                   vad_filter=False, condition_on_previous_text=False)
        words = [{"word": w.word.strip(), "start": round(pa + w.start, 3), "end": round(pa + w.end, 3),
                  "p": round(w.probability, 3)} for s in segs for w in s.words]
        rows.append({"a": a, "b": b, "text": " ".join(w["word"] for w in words).strip(), "words": words})
    classify(rows, lang)
    keep = [r for r in rows if r["label"] == "keep"]
    pauses = [round(keep[k + 1]["a"] - keep[k]["b"], 2) for k in range(len(keep) - 1)]
    return {"source": str(path), "duration": round(len(audio) / SR, 3), "threshold_dbfs": thr, "gap_s": gap,
            "chunks": rows, "keep_speech_s": round(sum(r["b"] - r["a"] for r in keep), 2),
            "pauses_between_kept": pauses, "counts": {lab: sum(r["label"] == lab for r in rows)
                                                       for lab in ("keep", "retake", "false_start", "editor", "noise")}}


def to_markdown(rep):
    lines = [f"# Triage · {Path(rep['source']).name}", "",
             f"{rep['duration']} s · kept speech {rep['keep_speech_s']} s · " +
             " · ".join(f"{k} {v}" for k, v in rep["counts"].items()), "",
             "| # | start | end | label | text | note |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(rep["chunks"]):
        lines.append(f"| {i} | {r['a']:.2f} | {r['b']:.2f} | {r['label']} | {r['text'].replace('|', '/')} | {r['note']} |")
    return "\n".join(lines) + "\n"


def main(argv):
    args, opts, i = [], {"--out": "triage", "--model": "large-v3", "--lang": os.environ.get("HEDITOR_LANG", "pt"),
                         "--thr": "-55", "--gap": "0.30"}, 0
    while i < len(argv):
        if argv[i] in opts:
            opts[argv[i]] = argv[i + 1]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    if not args:
        sys.exit(__doc__)
    from faster_whisper import WhisperModel
    model = WhisperModel(opts["--model"], device="cpu", compute_type="int8",
                         cpu_threads=int(os.environ.get("HEDITOR_ASR_THREADS", 4)))
    out = Path(opts["--out"])
    out.mkdir(parents=True, exist_ok=True)
    for src in args:
        rep = triage(Path(src), model, opts["--lang"], float(opts["--thr"]), float(opts["--gap"]))
        stem = Path(src).stem
        (out / f"{stem}.triage.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
        md = to_markdown(rep)
        (out / f"{stem}.triage.md").write_text(md)
        print(md)


if __name__ == "__main__":
    main(sys.argv[1:])
