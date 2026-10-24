# Raw takes: recording errors and asides to the editor

Scripted recordings (teleprompter, ad scripts, a batch of openings recorded in a row) never come clean: the speaker
pauses to read, restarts a sentence, stumbles inside a word, says the line twice with different energy, and talks to
whoever is going to edit ("cut that", "again", "corta aí, editor", "vamos editar essa parte"). Those asides break the
fourth wall: they are not content, they are **notes from the director to the editor**. Read them, follow them, and
make sure none of them reaches the cut.

Run the triage on every raw file before choosing anything:

```bash
heditor triage raw/*.mp4 --out triage --forbid "phrase the campaign forbids,another one"
```

It writes `triage/<stem>.triage.json` and `.md`: chunk table, asides to the editor, issues inside usable chunks and a
recording report. Nothing in it decides the cut on its own.

## 1. Asides to the editor (the fourth wall)

Every chunk labelled `editor` is listed with the chunk before, the chunk after, its intent and the action:

| Intent | Typical words | What to do |
|---|---|---|
| `cut` | "corta aí", "foi errado esse", "esquece", "cut that", "scratch that" | discard the take before (and whatever the aside points at: "esse aí" = the previous sentence) |
| `redo` | "de novo", "vou repetir", "vamos de novo", "again", "one more time" | the take before is rejected; use the next take of the same sentence |
| `marker` | "atenção", "editor", "valendo", "obrigado", "tchau", "rolling" | slate, attention or thanks: discard; the next chunk restarts the speech |
| `note` | "vamos editar essa parte", "essa última frase", "aqui entra a tela", "usa a segunda", "edit this part" | an editing instruction in the speaker's words. Follow it: replace the sentence with the retake, use the take he named, put the screen where he said. If it cannot be followed (the screen does not exist, the retake is incomplete), say so in the delivery |

Rules:
- An aside is never content: no caption, no frame of it, no sound of it in the cut. Check the assembled voice for the
  aside words (the n-grams of the cut's ASR) after prepare.
- The take right before an aside is presumed rejected (`retake`), even when it sounds fine; it comes back only if no
  later take of that sentence exists, and then the delivery says so.
- A chunk right after a run of asides ("Vamos para o terceiro passo agora") may itself be an aside said in a normal
  voice: the triage notes it ("right after an aside"); decide by meaning, not by the label.
- Record every aside and what was done with it (`DESIGN.md` or the edit report): the user wants to know his notes
  were heard.

## 2. Takes, false starts and stumbles

- `retake`: a later chunk repeats the sentence (same opening words or similar text). Keep **one whole take per
  sentence**. Prefer, in order: complete words and a finished intonation; starting with the eyes on the lens (when he
  reads between sentences, the first 0.3 s of a take often shows the eyes coming back from the prompter); energy and
  clarity; for openings, no hand on the chin in the first 3 s.
- `false_start`: a short chunk the next one restarts ("Você começa..." → "Você conecta..."): drop it.
- Issues inside a usable chunk, with word times:
  - `stutter` / `repeat`: "com com", the same two words twice. Cut one of them only at a real valley of the
    waveform; if the words are glued (no valley), use another take or keep the stumble rather than cutting a syllable.
  - `self_correction`: "conectada por trás, não, conectada ao sistema", "quer dizer", "ou melhor". Keep only the
    corrected version, cut at word boundaries, and never splice half of one version with half of the other.
  - `aside_inside`: an aside in the middle of a sentence; cut around it, or use another take.
  - `unclear`: low ASR confidence; listen (a mispronounced brand, a mumbled word). Do not fix it with a caption.
  - `forbidden`: a phrase the campaign forbids (`--forbid`); leave that sentence out or use a take without it.
- Never invent the missing piece: if the only complete take has an error, use it as is and flag it, or ask for a
  short re-record of that sentence.

## 3. Recording failures

From the `## Recording` section of the triage and a look at the frames:

| Failure | How it shows | What to do |
|---|---|---|
| Clipped audio | `clipping` events | cannot be repaired: avoid those words (another take) or report it; never "fix" with a limiter |
| Knock, clap, notification, someone talking off camera | `sounds_outside_speech` | keep the cut boundaries away from it; if it falls inside a sentence, use another take |
| Half the frames duplicated | `duplicated_frames_pct` ≈ 50 | the camera captured ~15 fps into a 30 fps file; motion looks stepped, not a render freeze; say so in the delivery |
| Camera moved, light changed, something entered the set | `picture_jumps_between_kept` (only the set around the speaker is measured, gestures do not count) | do not jump-cut between those takes in the same framing: alternate the framing (1.00 ↔ 1.06), cover the cut with a proof/insert, or match the colour |
| Mirrored image | text on the set reads backwards (calendar, shirt, posters) | `hflip` the source before anything and check the text again; every automatic check passes on a mirrored image |
| HDR (HLG/PQ) source | `ffprobe` colour transfer | convert with a compared tone map before editing; never pass HDR into the composition |
| Gaze off the lens, hand on the chin, mic in front of the mouth | vision on the first frame of each chosen take | choose another take for the hook; inside the body it is acceptable |
| Recording diverges from the script | triage text versus the script | what was said decides the screen; a step that was announced but not said appears locked without a name; list what was left out |

## 4. What goes in the delivery

Per file: the takes chosen (times), what was discarded and why (asides, retakes, false starts), every aside to the
editor and what was done with it, issues kept on purpose, recording failures and their workaround, what of the script
was not said, and the sentences that would need a re-record. Metrics and transcripts do not replace listening: say
which words to listen to.
