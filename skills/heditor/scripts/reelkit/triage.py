"""Triage of raw takes: split a recording at silence, transcribe every chunk alone and flag what must not be used.

Usage: triage.py <video> [<video> ...] [--out DIR] [--model large-v3] [--lang pt] [--thr -55] [--gap 0.30]
                 [--forbid "phrase one,phrase two"] [--no-tech]
Writes DIR/<stem>.triage.json and DIR/<stem>.triage.md (default DIR: ./triage) and prints the report.

Why: scripted recordings (teleprompter reading, ad scripts) come with reading pauses between sentences, false starts,
sentences said twice, stumbles and asides to the editor ("cut that", "again", "corta aí, editor", "vou falar de
novo") - the speaker breaking the fourth wall to talk to whoever edits. Transcribing the whole file hides them:
Whisper glues silences into words and invents repetitions ("WhatsApp. WhatsApp."). Here every chunk between silences
(10 ms RMS under `thr` dBFS for at least `gap` s) is transcribed alone, then labelled:

- keep         usable speech;
- retake       superseded by a later take of the same sentence (same opening words or similar text), or the take
               right before an aside to the editor (the speaker rejected it);
- false_start  a short chunk that the next chunk restarts;
- editor       an aside to the editor or the crew (strong cue anywhere, weak cue at the start of a short chunk);
- noise        breath/click/lip noise read as a word, very short chunks, stock Whisper hallucinations.

Three more layers for the review:
- instructions  every aside with its intent (redo / cut / marker / note), the chunk before and after, and what to do.
                A `note` is an editing instruction in the speaker's words ("vamos editar essa parte", "aqui entra a
                tela") and must be followed or reported, never just deleted.
- issues        inside usable chunks: stutters ("com com"), repeated bigrams, an aside or a self-correction in the
                middle of a sentence ("conectada por trás, não, conectada ao sistema"), unclear words (low ASR
                confidence) and phrases the campaign forbids (`--forbid`). Times are word times, to cut around them.
- tech          recording failures: clipped samples, loud sounds outside the speech (claps, knocks, notifications),
                duplicated frames (a phone capturing ~15 fps into a 30 fps file) and jumps of the set between
                consecutive kept chunks (camera moved, light changed, something entered the set; the speaker's own
                gestures are excluded by measuring only the top and the sides of the frame).

Nothing here decides the cut: read every non-`keep` line, every instruction and every issue, keep one whole take per
sentence and never splice half-sentences. Gaze off the lens, a hand on the chin and a mirrored image are checked by
vision on the first frame of each chosen take.
"""
import difflib
import json
import os
import re
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
INTENTS = {   # first match wins, in this order
    "pt": [("cut", ["corta", "pode cortar", "esquece", "nao vale", "foi errado", "errei", "nao usa"]),
           ("redo", ["de novo", "vou repetir", "deixa eu repetir", "repete", "outra vez", "mais uma vez", "volta ai"]),
           ("note", ["vamos editar", "edita", "essa parte", "essa frase", "aqui entra", "coloca", "usa a", "usa essa",
                     "troca", "tira", "deixa essa", "mostra a", "mostra o"]),
           ("marker", ["atencao", "editor", "vamos para", "agora vai", "gravando", "valendo", "obrigado", "valeu",
                       "tchau", "nao", "pera", "espera", "agora nao", "ops", "opa", "droga"])],
    "en": [("cut", ["cut", "scratch that", "dont use", "i messed up"]),
           ("redo", ["again", "redo", "one more time", "take two", "from the top", "start over"]),
           ("note", ["edit", "this part", "put the", "use the", "use this", "swap", "remove", "show the"]),
           ("marker", ["editor", "rolling", "action", "thanks", "thank you", "no", "wait", "hold on", "sorry", "oops"])],
}
SELF_CORRECTION = {"pt": ["quer dizer", "digo", "ou melhor", "perdao", "desculpa"], "en": ["i mean", "sorry", "or rather"]}
NEGATION = {"pt": "nao", "en": "no"}
WEAK_MAX_WORDS = 6
# Whisper's stock hallucinations on breaths, clicks and room tone (subtitle credits, channel outros)
HALLUCINATIONS = ["legendas pela comunidade", "amara org", "inscreva se no canal", "obrigado por assistir",
                  "subtitles by", "thanks for watching", "transcribed by"]
LABELS = ("keep", "retake", "false_start", "editor", "noise")


def _plain(text, lang):
    """Tokens without accents for cue matching ("não" -> "nao", "aí" -> "ai")."""
    tr = str.maketrans("áàâãéêíóôõúüç", "aaaaeeiooouuc")
    return [t.translate(tr) for t in notation_tokens(text, lang)]


def _has(seq, cue):
    return any(seq[i:i + len(cue)] == cue for i in range(len(seq) - len(cue) + 1))


def _find(seq, cue):
    return next((i for i in range(len(seq) - len(cue) + 1) if seq[i:i + len(cue)] == cue), None)


def is_editor(text, lang="pt"):
    """Strong cue anywhere, or a short chunk (<= WEAK_MAX_WORDS tokens) that starts with a weak cue."""
    toks = _plain(text, lang)
    if any(_has(toks, _plain(c, lang)) for c in STRONG.get(lang, [])):
        return True
    return len(toks) <= WEAK_MAX_WORDS and any(toks[:len(cue)] == cue for cue in (_plain(c, lang) for c in WEAK.get(lang, [])))


def aside_intent(text, lang="pt"):
    """redo (say it again), cut (discard what came before), marker (attention/slate/thanks) or note (an instruction)."""
    toks = _plain(text, lang)
    for intent, cues in INTENTS.get(lang, []):
        if any(_has(toks, _plain(c, lang)) for c in cues):
            return intent
    return "note"


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


ACTIONS = {
    "redo": "the take before is rejected: use the next take of the same sentence",
    "cut": "discard the take before (and anything the aside points at)",
    "marker": "slate/attention/thanks: discard; the next chunk restarts the speech",
    "note": "an editing instruction in the speaker's words: follow it (replace, keep, add a screen...) or report why not",
}


def instructions(chunks, lang="pt"):
    """Every aside to the editor with its intent, neighbours and the action it asks for."""
    out = []
    for i, c in enumerate(chunks):
        if c["label"] != "editor":
            continue
        prv = next((k for k in range(i - 1, -1, -1) if chunks[k]["label"] not in ("noise", "editor")), None)
        nxt = next((k for k in range(i + 1, len(chunks)) if chunks[k]["label"] not in ("noise", "editor")), None)
        intent = aside_intent(c["text"], lang)
        out.append({"chunk": i, "a": c["a"], "b": c["b"], "text": c["text"], "intent": intent, "action": ACTIONS[intent],
                    "before": None if prv is None else {"chunk": prv, "text": chunks[prv]["text"]},
                    "after": None if nxt is None else {"chunk": nxt, "text": chunks[nxt]["text"]}})
    return out


def _word_tokens(words, lang):
    """[(token, start, end, p, raw_word)] flattening each ASR word into its plain tokens."""
    out = []
    for w in words:
        for t in _plain(w.get("word", ""), lang):
            out.append((t, w.get("start"), w.get("end"), w.get("p", 1.0), w.get("word", "")))
    return out


def chunk_issues(chunk, lang="pt", forbid=(), unclear_p=0.35):
    """Problems inside one chunk, with word times: stutter, repeat, aside_inside, self_correction, forbidden, unclear."""
    wt = _word_tokens(chunk.get("words", []), lang)
    toks = [x[0] for x in wt]
    issues = []

    def add(kind, i0, i1, why):
        if wt:
            issues.append({"kind": kind, "start": wt[i0][1], "end": wt[i1][2], "text": " ".join(x[4] for x in wt[i0:i1 + 1]),
                           "why": why})

    for i in range(len(toks) - 1):
        if toks[i] == toks[i + 1] and not toks[i].isdigit():
            add("stutter", i, i + 1, "the same word twice in a row")
    for i in range(len(toks) - 3):
        if toks[i:i + 2] == toks[i + 2:i + 4]:
            add("repeat", i, i + 3, "the same two words twice in a row")
    if chunk.get("label") in ("keep", "retake") and len(toks) >= 4:
        for cue in STRONG.get(lang, []):
            k = _find(toks, _plain(cue, lang))
            if k is not None:
                add("aside_inside", k, min(len(toks) - 1, k + len(_plain(cue, lang)) - 1),
                    "an aside to the editor inside a sentence: cut around it")
        for cue in SELF_CORRECTION.get(lang, []):
            k = _find(toks, _plain(cue, lang))
            if k is not None and k >= 2:
                add("self_correction", max(0, k - 2), min(len(toks) - 1, k + 2), "the speaker corrects himself")
        neg = NEGATION.get(lang)
        for k in range(2, len(toks) - 1):
            if (toks[k] == neg and wt[k - 1][4].rstrip().endswith((",", "...", "…")) and len(toks[k + 1]) >= 4
                    and toks[k + 1] in toks[max(0, k - 5):k]):
                add("self_correction", max(0, k - 3), min(len(toks) - 1, k + 2), "restated after a 'no': keep only one version")
    for phrase in forbid:
        cue = _plain(phrase, lang)
        k = _find(toks, cue) if cue else None
        if k is not None:
            add("forbidden", k, k + len(cue) - 1, f"forbidden phrase: {phrase}")
    for i, x in enumerate(wt):
        if x[3] is not None and x[3] < unclear_p and len(x[0]) >= 3:
            add("unclear", i, i, f"low ASR confidence ({x[3]:.2f}): mispronounced or mumbled? listen")
    return issues


def _decode48(path):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)


def _gray(path, t, w=64):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(path), "-frames:v", "1", "-vf",
                          f"scale={w}:{w * 16 // 9},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).astype(np.float64) if len(raw) == w * (w * 16 // 9) else None


def _background(g, w=64):
    """Top 20 % of the frame and the outer 15 % columns down to mid-height: the set, not the speaker."""
    h = w * 16 // 9
    a = g.reshape(h, w)
    top, mid = a[: int(h * 0.2)], a[int(h * 0.2): int(h * 0.5)]
    side = int(w * 0.15)
    return np.concatenate([top.ravel(), mid[:, :side].ravel(), mid[:, -side:].ravel()])


def tech_report(path, chunks, has_video=True, burst_db=-40.0, jump=6.0, light=8.0):
    """Recording failures: clipping, loud sounds outside speech, duplicated frames, picture jumps between kept chunks."""
    x = _decode48(path)
    clip = np.abs(x) >= 0.995
    idx = np.flatnonzero(clip)
    runs = []
    for i in idx:
        if not runs or i - runs[-1][1] > 480:
            runs.append([i, i])
        else:
            runs[-1][1] = i
    rep = {"clipping": {"samples_pct": round(float(clip.mean() * 100), 4), "events": len(runs),
                        "times": [round(a / 48000, 2) for a, _ in runs[:12]]}}
    hop = 480
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-12)
    inside = np.zeros(n, bool)
    for c in chunks:
        if c["label"] != "noise":
            inside[max(0, int((c["a"] - 0.1) * 100)): min(n, int((c["b"] + 0.1) * 100))] = True
    loud = np.flatnonzero((db > burst_db) & ~inside)
    bursts = []
    for i in loud:
        if not bursts or i - bursts[-1]["_i"] > 20:
            bursts.append({"t": round(i / 100, 2), "rms_db": round(float(db[i]), 1), "_i": i})
        else:
            bursts[-1]["rms_db"] = max(bursts[-1]["rms_db"], round(float(db[i]), 1))
            bursts[-1]["_i"] = i
    rep["sounds_outside_speech"] = [{k: v for k, v in b.items() if k != "_i"} for b in bursts[:20]]
    if not has_video:
        return rep
    err = subprocess.run(["ffmpeg", "-i", str(path), "-map", "0:v:0", "-vf", "mpdecimate", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    kept = re.findall(r"frame=\s*(\d+)", err)
    total = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                            "stream=nb_read_packets", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    if kept and total.strip().isdigit():
        rep["duplicated_frames_pct"] = round(100 * (1 - int(kept[-1]) / int(total)), 1)
    keep = [c for c in chunks if c["label"] == "keep"]
    jumps = []
    for c, d in zip(keep, keep[1:]):
        g0, g1 = _gray(path, c["b"] - 0.1), _gray(path, d["a"] + 0.1)
        if g0 is None or g1 is None:
            continue
        b0, b1 = _background(g0), _background(g1)     # the set around the speaker: gestures do not count
        diff, dl = float(np.abs(b0 - b1).mean()), float(b1.mean() - b0.mean())
        if diff > jump or abs(dl) > light:
            jumps.append({"after": round(c["b"], 2), "before": round(d["a"], 2), "background_diff": round(diff, 1),
                          "luma_change": round(dl, 1),
                          "why": "light changed" if abs(dl) > light else "camera moved, framing changed or something entered the set"})
    rep["picture_jumps_between_kept"] = jumps
    return rep


def _load(path):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)


def _db(audio, win=0.01):
    n = int(SR * win)
    frames = len(audio) // n
    return 20 * np.log10(np.sqrt(np.mean(audio[: frames * n].reshape(frames, n) ** 2, axis=1)) + 1e-12)


def _has_video(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=index", "-of",
                          "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return bool(out.strip())


def triage(path, model, lang="pt", thr=-55.0, gap=0.30, forbid=(), tech=True):
    audio = _load(path)
    rows = []
    for a, b in voiced_chunks(_db(audio), thr=thr, gap=gap):
        pa, pb = max(0.0, a - 0.15), min(len(audio) / SR, b + 0.15)
        segs, _ = model.transcribe(audio[int(pa * SR): int(pb * SR)], language=lang, beam_size=5, word_timestamps=True,
                                   vad_filter=False, condition_on_previous_text=False)
        words = [{"word": w.word.strip(), "start": round(pa + w.start, 3), "end": round(pa + w.end, 3),
                  "p": round(w.probability, 3)} for s in segs for w in s.words]
        rows.append({"a": a, "b": b, "text": " ".join(w["word"] for w in words).strip(), "words": words})
    return build_report(path, rows, round(len(audio) / SR, 3), lang, thr, gap, forbid, tech)


def build_report(path, rows, duration, lang="pt", thr=-55.0, gap=0.30, forbid=(), tech=True):
    classify(rows, lang)
    for r in rows:
        r["issues"] = chunk_issues(r, lang, forbid) if r["label"] in ("keep", "retake") else []
    keep = [r for r in rows if r["label"] == "keep"]
    pauses = [round(keep[k + 1]["a"] - keep[k]["b"], 2) for k in range(len(keep) - 1)]
    rep = {"source": str(path), "duration": duration, "threshold_dbfs": thr, "gap_s": gap, "chunks": rows,
           "instructions": instructions(rows, lang), "keep_speech_s": round(sum(r["b"] - r["a"] for r in keep), 2),
           "pauses_between_kept": pauses, "counts": {lab: sum(r["label"] == lab for r in rows) for lab in LABELS},
           "issues_in_kept": sum(len(r["issues"]) for r in keep)}
    if tech:
        rep["tech"] = tech_report(path, rows, _has_video(path))
    return rep


def to_markdown(rep):
    lines = [f"# Triage · {Path(rep['source']).name}", "",
             f"{rep['duration']} s · kept speech {rep['keep_speech_s']} s · " +
             " · ".join(f"{k} {v}" for k, v in rep["counts"].items()) + f" · issues in kept {rep['issues_in_kept']}", "",
             "| # | start | end | label | text | note |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(rep["chunks"]):
        flags = "; ".join(f"{x['kind']} {x['start']:.2f}" for x in r.get("issues", []))
        note = "; ".join(s for s in (r["note"], flags) if s)
        lines.append(f"| {i} | {r['a']:.2f} | {r['b']:.2f} | {r['label']} | {r['text'].replace('|', '/')} | {note} |")
    if rep["instructions"]:
        lines += ["", "## Asides to the editor (fourth wall)", "",
                  "| # | at | said | intent | before | after | action |", "|---|---|---|---|---|---|---|"]
        for x in rep["instructions"]:
            before = f"#{x['before']['chunk']} {x['before']['text']}" if x["before"] else ""
            after = f"#{x['after']['chunk']} {x['after']['text']}" if x["after"] else ""
            lines.append(f"| {x['chunk']} | {x['a']:.2f} | {x['text']} | {x['intent']} | {before} | {after} | {x['action']} |")
    issues = [(i, x) for i, r in enumerate(rep["chunks"]) for x in r.get("issues", [])]
    if issues:
        lines += ["", "## Issues inside usable chunks", "", "| # | kind | start | end | words | why |",
                  "|---|---|---|---|---|---|"]
        for i, x in issues:
            lines.append(f"| {i} | {x['kind']} | {x['start']:.2f} | {x['end']:.2f} | {x['text']} | {x['why']} |")
    tech = rep.get("tech")
    if tech:
        lines += ["", "## Recording", ""]
        cl = tech["clipping"]
        lines.append(f"- Clipping: {cl['events']} events ({cl['samples_pct']} % of samples)"
                     + (f" at {', '.join(str(t) for t in cl['times'])} s" if cl["events"] else ""))
        snd = tech["sounds_outside_speech"]
        lines.append(f"- Sounds outside the speech: {len(snd)}" +
                     (": " + ", ".join(f"{s['t']} s ({s['rms_db']} dB)" for s in snd) if snd else ""))
        if "duplicated_frames_pct" in tech:
            lines.append(f"- Duplicated frames: {tech['duplicated_frames_pct']} % "
                         "(≈50 % = the camera captured half the frame rate; not a render freeze)")
        for j in tech.get("picture_jumps_between_kept", []):
            lines.append(f"- Picture jump between {j['after']} s and {j['before']} s: {j['why']} "
                         f"(set diff {j['background_diff']}, luma {j['luma_change']:+})")
    return "\n".join(lines) + "\n"


def main(argv):
    args, opts, i = [], {"--out": "triage", "--model": "large-v3", "--lang": os.environ.get("HEDITOR_LANG", "pt"),
                         "--thr": "-55", "--gap": "0.30", "--forbid": ""}, 0
    tech = "--no-tech" not in argv
    argv = [a for a in argv if a != "--no-tech"]
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
    forbid = [p.strip() for p in opts["--forbid"].split(",") if p.strip()]
    out = Path(opts["--out"])
    out.mkdir(parents=True, exist_ok=True)
    for src in args:
        rep = triage(Path(src), model, opts["--lang"], float(opts["--thr"]), float(opts["--gap"]), forbid, tech)
        stem = Path(src).stem
        (out / f"{stem}.triage.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
        md = to_markdown(rep)
        (out / f"{stem}.triage.md").write_text(md)
        print(md)


if __name__ == "__main__":
    main(sys.argv[1:])
