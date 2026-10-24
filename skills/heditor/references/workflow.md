# Workflow

Commands assume `. ~/.heditor/env.sh`. `<work>` is one folder per cut (e.g. `cuts/benchmark-v1`).

This is the Reels workflow (30-70 s, 9:16). For a whole class, live or YouTube video (minutes to hours, 16:9 or
any other format profile) use the long-form workflow in `long-form.md` (`heditor new --long`, `heditor long ...`).
Both share the same rules: speech at 1×, cuts only at word boundaries, voice-first mix, readable captions, truth.

## 1. Intake

Collect (ask only what you cannot infer): source video path or URL, target platform (Reels/Shorts/TikTok, all 1080×1920; a long video for YouTube/a course → `long-form.md`; another canvas → `heditor formats`), target length (default 30–70 s), mode/style, CTA (default: comment question tied to the topic + follow the brand handle), language of the speech, anything that must not appear (names, private data). Confirm `~/.heditor/brand.json` is filled.

## 2. Probe

```bash
heditor probe <video> 5 60 300 900        # frames in ./probe/
```
Look at the frames: full-frame selfie, studio camera, meeting recording with a webcam tile, screen share with a small camera? Measure the speaker crop in source pixels (ffmpeg `crop=w:h:x:y`). The crop must contain only the speaker and stop above any name label of the meeting software. Aim for 4:3 or 3:4. If the camera is missing in part of the recording, choose excerpts where it is visible.

## 3. Transcribe and select

```bash
heditor transcribe <video> 0 <duration_s> <work>/qa/asr-full.json "names, jargon, brand terms"
```
For long recordings transcribe in windows (e.g. 600 s) or use an existing transcript to locate candidates, then re-transcribe ±90 s around each candidate (timestamps from meeting transcripts are approximate).

**Scripted recordings (teleprompter, ad scripts, a batch of openings):** run `heditor triage <video...> --out <dir>`
first and follow `raw-takes.md`. The speaker pauses to read between sentences, restarts, says a sentence twice and talks to the editor ("cut
that", "again", "I'll say it again"); a whole-file ASR glues the silences into words and invents repetitions. Triage
splits the file at silence, transcribes each chunk alone (large-v3, no context, no vocabulary prompt) and labels it
`keep`, `retake` (superseded by a later take, or the take right before an aside), `false_start`, `editor` (aside to
the crew) or `noise` (breaths and clicks Whisper turns into words). It also lists every aside with its intent (`cut`,
`redo`, `marker`, `note`: a `note` is an editing instruction to follow), issues inside usable chunks (stutters,
self-corrections, asides mid-sentence, unclear words, `--forbid` phrases) and recording failures (clipping, knocks,
duplicated frames, the set moving between takes). Read every non-`keep` line and every `keep` marked
"right after an aside", choose one whole take per sentence (prefer the one that starts looking at the lens), and build
the BLOCKS only from those chunks. After prepare, the assembled voice must have zero asides and zero repeated
sentences (check the n-grams of the cut's ASR). The recording diverges from the script: what was said decides what
goes on screen; list what was left out.

Selection rules:
- A complete, self-contained idea: hook → thesis → explanation/example → conclusion. 30–70 s is the sweet spot.
- The hook (first 1–3 s) must be a real spoken line. A cold open (strongest line first, then the argument from the start) is allowed when the line appears later in the speech; it is a stylistic choice (Ruptura, creative mode).
- Remove: repetitions, false starts, long digressions, references to things the viewer cannot see ("as you can see on screen", chat questions), names of third parties, private information. Cut only at clean word boundaries.
- Keep: the speaker's voice and rhythm, speed 1×. No dead air: `prepare_cut` trims every block edge to 0.08 s before the first voiced window and 0.12 s after the last one, and shortens internal pauses longer than 0.35 s to ~0.24 s (defaults `lead`, `tail`, `min_pause`, `edge`). A block boundary snaps to the quietest point of its radius, so without the edge trim each junction keeps silence from both sides (0.8–1.3 s gaps that read as uncut pauses).
- Never: invent speech, reorder words inside a sentence, splice fragments into a sentence that was not said, change the meaning.

## 4. Prepare

```bash
heditor new <work> <video>
# edit <work>/prepare.py: CROP and BLOCKS = [(key, start, end, end_radius, start_radius), ...]
heditor prepare <work>                      # camera-src.mp4, voice-raw.wav, edl.json
heditor words <work> "names, jargon"        # words.json + words-reviewed.json
```
Review `words-reviewed.json`: fix spelling, brand names and technical terms (never timings). Profanity can be masked on screen through `rk.load_words(path, censor={"word": "w*rd"})`; audio stays untouched. Check the first/last word of each block in the ASR: if a word is clipped, widen that block boundary and prepare again. Then run `heditor gaps <work>`: it lists every silence ≥ 0.2 s left in the assembled voice (junction or internal, with the words around it) and fails when one exceeds 0.45 s. Fix the BLOCKS or the trim parameters until it passes; never leave pause cleanup for after the render.

## 5. Design

Fill `<work>/DESIGN.md` (template provided). In a fixed style, adapt the style's scene grammar to this speech. In creative mode follow `creative-mode.md`. Decide the music (`music:<id>` from `assets/catalog.json`, see `sound-design.md`) and the drop point.

## 6. Build

Rewrite `<work>/build.py`. It must expose `WORK` and `build(track, drop_s)` that writes `composition/index.html`, `plan.json` (`duration`, `voice_end`, `keys`, `captions`, `sound_events`, `music`, optional `music_ref`, `cta_boost_db`, `allowed_numbers`) and `captions.json`. Duration = voice end + CTA (≥ 4 s). See `kit-api.md` for the helpers. Generate camera variants with `rk.styled_camera(work, name, vf)` when the world needs another look.

## 7. Produce

```bash
heditor produce <work> music:955 30        # track and drop second inside the track
```
`heditor produce` must regenerate `voice-master.wav` from the current `voice-raw.wav`, including when a revision is cloned from an earlier project. Checking only whether the normalized file exists can mix the old, longer speech into the new camera and captions and truncate the ending. Compare both WAV durations against `plan.voice_end` before rendering; the revision integrity test enforces this. After muxing, also transcribe the final spoken sentence separately if full-length ASR omits it.

Choose the mix profile first (`plan["mix"]`, `sound-design.md`): `voice` for organic Reels and class excerpts, `presence` for paid ads and creative mode. Profile the track with `heditor music <music:ID|file>` and set each section's `src` so its kick entries, breakdowns and lifts fall on the speech turns.

Read `balance` against the profile (`rk.mix_targets`): `voice` music ≤ -21.5 dB, background p95 ≤ -12 dB, < 5 % within 10 dB; `presence` −15 / −7 dB, < 30 %. Check `music_gaps` (the bed vanished: quiet intro, long `muffled`/`lowpass` section) and `long_filtered_sections`. If the background is too loud, lower SFX gains that fall on words or move them into gaps; if the bed vanishes, pick another `src`, shorten the filtered section or raise that section's `gain_db`.

## 8. QA before render

```bash
heditor lint <work>                                     # 0 errors (warnings about caption structure are normal)
heditor preview <work> 0.05,0.8,2.5,4,6,8,...          # 18–24 times across the cut, incl. every scene change and the CTA
heditor test <work>
python $HEDITOR_KIT/camera_sync_check.py <work>   # every camera variant aligned with camera-src (offset 0, same frame count)
python $HEDITOR_KIT/camera_sync_check.py <work> --source   # camera-src and voice vs the original recording through edl.json
```
Inspect `qa/sheet.jpg` with vision: overlaps, clipped text, text above y=270, face covered, captions colliding with graphics, low-contrast active word, placeholder-looking elements, generic or meaningless decoration. Fix and preview again (name sheets sheet-b, sheet-c…). In batches, also compare sheets across videos.

## 9. Render and finalize

```bash
heditor render <work> 2          # workers; a 60 s cut takes ~5–15 min depending on CPU
heditor finalize <work> <slug>-1080x1920.mp4
heditor asr-check <work>       # required in the presence profile; MASKED spans -> local dips in the bed
```
`finalize` muxes `master.wav`, guards true peak after AAC (first an oversampled peak limiter that keeps −14 LUFS; a lower loudnorm TP only as a fallback), measures loudness, freezes, top margin and the hook metrics of the first 15 s (`first_15s`: voice share and words; paid ads that hold attention keep ≥ 90 % voice and ≥ 38 words there), and builds `qa/final-contact-sheet.jpg` (40 frames). Review the sheet with vision. Read `quality-gates.md` for how to interpret freezes and margin flags. `asr-check` folds notation before comparing ("pra"/"para", "7h30"/"sete e meia", "5"/"cinco"), lists those differences apart as `NOTATION`, and only `MASKED` spans can need a dip; confirm each one with a short large-v3 window on both files before touching the mix.

New openings for a video that is already running (hook tests): keep the body identical and follow `hook-variants.md`
(`heditor splice find-cut` to find the frame, `heditor splice` to join the rendered opening to the delivered file).

## 10. Deliver

Give the user the MP4 path (or upload where they asked), duration, format/style, music, and what was verified. Say plainly that metrics and transcripts do not replace listening. Keep previous versions; new versions get `-v2`, `-v3`.
