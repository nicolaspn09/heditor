# Hook variants: new openings for a video that already performs

When an ad (or an organic cut) already converts and the team wants to test new hooks, only the opening changes. The
body must stay identical to the file that is running, so the difference measured in hook rate, hold and cost per
result comes from the opening alone. Do not change music, SFX, cuts or grading of the body "on the way" (not even a
music swap planned before): that mixes two variables in the test. Name each version after the original with a
suffix per opening: `<name>_v<N+1>-abA.mp4`, `-abB`, `-abC`.

## Before editing

1. **Triage the new takes** with `heditor triage` (see `workflow.md`): scripted openings are usually recorded in a
   row, with reading pauses, retakes and asides to the editor. Use only `keep` chunks and pick the take that starts
   looking at the lens, with energy and without a hand on the chin in the first 3 s.
2. **Measure the splice point** in the delivered file: `heditor splice find-cut <body.mp4> <from_s> <to_s>` lists the
   first black frame after a lit one, the biggest picture jumps and the audio level there. Read also the body's
   `plan.json` (music sections, their `src`) and `words-reviewed.json` (last word removed, first word kept).
3. **Choose the route:**

| Route | When | How |
|---|---|---|
| A, splice | The splice falls on a hard cut of the delivered file (cut to black, change of world, a card) or the opening goes before the whole body | Render only the opening as its own heditor work (reuse the CSS/JS of the body's `build.py`) and splice it with `heditor splice` onto the delivered MP4 from the cut frame. The body is never re-edited. |
| B, project copy | The splice falls inside a phrase or a continuous music section (e.g. removing a word that touches the next one with a 20 ms valley) | Copy the project (`cp -cR`, an APFS clone, instant) and run the body's build with the new take as an extra source in the EDL; body, music and SFX stay the same, only shifted in time. |
| C, rebuild | The file changes inside and the project media no longer exist | Rebuild from the raw recordings and the versioned scripts; before editing, reproduce the delivered version and compare duration (±1 frame), 20 frames side by side, audio correlation and loudness (±0.5 LU). |

## Common to every route

- **End the opening in the state of the body's frame 0.** Copy the CSS and initial values of the body's build (plates,
  panels, seals, masks of the cut-out speaker) and calibrate the speaker's scale and position by the face box
  (MediaPipe) of the opening's last rendered frame against the body's first frame; the average of the take is off by
  5–10 %. If the body shows the speaker cut out over a world, the opening uses the cut-out in the same world and
  converges to that scale and position by the splice, so the cut never reads as a second start.
- **Colour matched to the body.** Same grade as the body, checked side by side on skin and wall at both ends. A new
  recording session under different LED light needs per-channel gain on the RGB (alpha untouched); the average of the
  raw take is not enough.
- **Continuous music at the splice.** An opening of duration d plays the same track from `src_body − d` to `src_body`
  (the `src` of the body's music section at the splice); if `src_body < d`, start at 0 with a short fade-in.
- **Level.** Short-term loudness 1.5 s before × after and S (3 s) centred on the splice, new versus original, within
  ±1 LU; final −14 LUFS and true peak ≤ −1.5 dBTP after AAC. Gain and limiter only on the opening. If the old cut had
  silent black before a card and the new opening speaks up to it, these numbers cannot close: record the momentary
  loudness of the last opening word against the first body word instead, and never drop the hook below the body's
  speech level just to close the number.
- **A seal or overlay** (campaign date, offer name) from the end of the opening to the CTA is the only visible change
  in the body. Render it once as a transparent PNG in the render Chrome, use it as an `<img>` in the opening and as
  `--overlay` in `heditor splice`, in a place the body's 40-frame sheet (with enlarged crops of the candidate area)
  shows free. If the body already switches to its own seal later, end yours before that switch so two seals never
  overlap (`--overlay-until`).
- **Frame 0 of the opening.** What must be visible at t = 0 (title, proof, first caption with the active word, cursor)
  is visible by CSS or `gsap.set` outside the timeline; a `tl.set`/`fromTo` at 0 may not show in the first rendered
  frame. With frame-by-frame seeking, a finished `to` loses against an older `fromTo` still active: to hide something
  another animation controls, animate its container.

## Route A details (what `heditor splice` does and why)

- The splice frame K is the index of the first black frame (or of the picture jump), found by per-frame luma, not only
  by `blackdetect`.
- HyperFrames renders `round(D·fps)+1` frames; only `round(D·fps)` are used, otherwise 33 ms of silence enter and the
  bed stutters at the splice. Video: opening `trim=end_frame=N` + body `trim=start_frame=K`, concatenated, encoded
  once, with `-frames:v N + (total − K)` (`-shortest` cuts the last body frame).
- Body audio is decoded whole **without `-ss`** and cut by sample: `-ss 0` on an AAC file drops 1024 samples beyond the
  encoder priming and the body would come 21 ms early. The opening master is zero-padded to `N/fps · 48000` and an
  equal-power crossfade of 5–10 ms ends exactly on the cut (with K = 0 the opening tail fades out instead).
- The video splice and the audio splice do not have to fall on the same sample when the body cuts to a card: with the
  same time mapping (`out = body − K/fps + N/fps`), switch to the body audio in its digital silence before the card hit
  and let the tail of the opening's last word end whole. Use `N/fps` exactly in measurements: rounded seconds report a
  false lag of 1–2 samples.
- The report (`<out>.splice.json`) proves the body untouched: audio correlation ≥ 0.999 with lag 0 against the
  delivered file, frame difference on sampled body frames (non-zero only where the overlay sits), and the opening audio
  aligned with what was written (a limiter without latency compensation shifts it 1 ms).

## Route B details

- Mount the new take as one more source and repeat the body's ranges unchanged. Body words = the delivered version's
  `words-reviewed.json` shifted by the EDL delta; build anchors = old anchors + delta. Check by stems (voice, music,
  SFX, master) against the delivered version over the body window.
- Cut-out speaker: run the matte only on the opening frames and concatenate with the old alpha cut by the same frames
  (decode VP9 with `-c:v libvpx-vp9` on the input, re-encode with `alpha_mode=1`); check alpha × camera by luma
  difference with offsets −2..+2 (ties on duplicated frames are normal).
- The automatic bed gain uses the p95 of all speech windows: a different opening moves the body's music 0.6–0.8 dB.
  Compensate in the opening's `bed_p95_db` target until the body's music matches the delivered one (±0.1 dB).
- A splice that removes words at the start of the body: the delivered version's ASR may put the next word ~0.15 s
  early; cut and caption by the RMS attack and confirm with a short ASR of the assembled voice.
- New CSS classes in a large build: prefix them (a new class can inherit the tracking of an old one and clip the
  text). `opacity` on a `preserve-3d` parent flattens the 3D and shows the mirrored back face: fade the faces.

## Route C details

- Restore the old project structure from the versioned scripts, fix paths and download the music and SFX again by the
  ids in `plan.json` and `sound-events.json` (compare their profiles with the archived ones). Audio cuts the build reads
  ready-made are rebuilt by finding each start by correlation with the delivered audio.
- Approved reproduction = same frame count, decoded audio correlation 1.0, same loudness and mean SSIM ≥ 0.99 on 20
  frames. The matte is the only acceptable difference; document it.
- Size the editing task: rebuild + reproduction + four versions in one agent run exhausts its iteration budget before
  the renders. Give each run at most the rebuild and two versions, and require in every work a `render_chain.sh`
  (render + finalize) and command-line QA scripts, so the coordinator can finish without reopening the run.

## What to say on delivery

The hook gate (voice ≥ 90 % and ≥ 38 words in the first 15 s; `first_15s` in `qa/final-verification.json` for a full
build, measured on the spliced file for route A) may fail
only because of the body (blacks and cards right after the splice): record the number and say it changes only by
editing the body. Ask for a listen of the splice and of the words that ASR reads differently from the captions.
