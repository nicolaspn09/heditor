# Quality gates

A cut is delivered only when all required gates pass (or a flagged item was inspected and documented as intentional).

| Gate | Command / file | Pass |
|---|---|---|
| Speech integrity | `words-reviewed.json`, `edl.json` | only spoken words, 1× speed, no clipped words at block edges (check ASR at each junction) |
| Dead air | `heditor gaps <work>` | no silence > 0.45 s inside the speech (junctions included); run right after prepare |
| Design | `DESIGN.md` | analysis, mode/style, beat sheet, music, CTA, risks written before building |
| Lint | `heditor lint <work>` | 0 errors (caption-structure warnings are normal) |
| Mix balance | `qa/balance.json` | profile targets (`rk.mix_targets`): `voice` music ≤ -21.5 dB vs voice (median), background p95 ≤ -12 dB, < 5 % windows within 10 dB; `presence` −15 / −7 dB, < 30 % |
| Music presence | `qa/balance.json` `music_gaps` | no run where the bed's presence band stays under the floor longer than the profile allows (voice 8 s, presence 2 s), outside declared `silence` |
| Previews | `heditor preview` + vision | no overlaps, clipped text, face coverage, low-contrast active word, placeholder look, text above 270 px |
| Distinctness (batches) | vision on contact sheets | videos do not look like the same template |
| Tests | `heditor test <work>` | all pass (captions = words, no overlap, CTA with handle + Follow/Following, events in timeline, balance, no unspoken numbers, no "illustrative"/placeholder tags, no dead air) |
| Facts on screen | `DESIGN.md` | every on-screen fact that the speaker did not say (documentary notes, chart points) is verified in a cited source, listed with it, and its digits are in `allowed_numbers` |
| Render | `heditor render` | exit 0 |
| Final file | `qa/final-verification.json` | no decode errors, -15 ≤ LUFS ≤ -13, true peak ≤ -1.5 dBTP, audio/master correlation ≥ 0.99, top margin ≥ the profile's `safe_top` (270 in 9:16) |
| Hook (paid ads, advisory) | `qa/final-verification.json` `first_15s` | voice share ≥ 0.90 and ≥ 38 words in the first 15 s; dramatic pauses, blacks and slow cards after 15 s. Record the number when the body of a hook test makes it impossible |
| Final frames | `qa/final-contact-sheet.jpg` + vision | no defects |
| Masking | `heditor asr-check <work>` | master similarity ≥ 0.90 and ≥ (clean voice − 0.03) on notation-folded words, exit 0; required in `presence`; fix `MASKED` spans with local dips (`NOTATION` spans need nothing) |
| Hook test (route A) | `<out>.splice.json` from `heditor splice` | frame count = opening + body from the cut, body audio correlation ≥ 0.999 with lag 0, opening audio lag 0, true peak ≤ −1.5 dBTP, short-term loudness at the splice within ±1 LU of the original cut (or the exception documented) |

## Reading flags
- **Freezes** (`freezedetect`, 0.3 s) are advisory. They fire on intentional holds (CTA built in steps, final card, title and dated chapter cards), planned blackouts and when the camera is small inside a UI and the speaker is still. Extract the flagged frames and confirm with vision; fail only if the picture is really stuck (a video that did not load, a broken scene).
- **Top margin** by pixels also fires on full-width decorative transitions (stripe wipes, flashes). Check the flagged frames; real text/graphics above 270 px must be fixed.
- **CTA test on paid ads**: `test_duration_and_cta` expects the brand handle and a Follow/Following card. An ad with a "Learn more" CTA fails it by design; record the expected failure and keep every other test green.
- **True peak** after AAC: finalize first limits only the peaks (4× oversampled limiter with latency compensation, loudness kept at −14 LUFS) and falls back to a dynamic loudnorm with a lower TP, which ends ~0.8–1 dB quieter; `tp_guard.method` says which one ran.
- **asr-check notation**: `HEDITOR_ASR_CHECK_STRICT=1` gates on the raw (unfolded) similarity, the pre-2.9 behaviour.

## Final checklist for the delivery message
Format/style and why; duration; music (title, artist, licence); what was verified (gates above); flagged items and decisions; what was not verified (nobody listened; colour on other screens); file path/link. Never publish without explicit permission.

## Long-form gates

Long-form videos (`heditor long finalize` / `heditor long qa`) have their own report, `qa/long-report.{json,md}`:
duration and canvas, full decode, loudness (default −14 LUFS ±1 LU, true peak ≤ −1 dBTP, from `long.json`
`loudness`), audio/master correlation, camera/screen/voice sync against the source through the EDL, sampled-window
ASR (mean ≥ 0.85), chapter rules (first 0:00, ≥ 3, ≥ 10 s, each on a word), segment seams (frame counts, no black or
duplicated frame at a boundary, `qa/seams.jpg`) and contact sheets `qa/long-sheet-NN.jpg` (≤ 1400 px) for vision.
`heditor test <work>` runs the Reel integrity tests in long-form mode (no 180 s cap, CTA by `cta.kind`, pauses up to
0.6 s, captions optional). Details in `long-form.md`.

## Camera sync

`python $HEDITOR_KIT/camera_sync_check.py <work>` must print OK for every `camera-*.mp4` used by the composition before rendering, especially after any change to the cut. Captions and ASR do not detect a picture that drifted from the voice. `--source` (and `heditor long sync <work>`) goes further: it compares the assembled camera, screen and voice with the original recording at the source times the EDL maps to (picture offset ≤ 1 frame, voice lag ≤ 10 ms), so picture and voice are proven in sync with each other.

## Leftover elements

Preview a few frames long after every short-lived element (labels, chips, notes shorter than ~0.6 s) and in the CTA: anything still visible there that belongs to an earlier beat is a timeline bug (overlapping in/out tweens), not a design choice. Do this check on frames extracted from the rendered MP4 as well: the render seeks frame by frame in order and an
overlapping tween can win there while the preview (a single seek) hides it (`references/gsap-craft.md` § Sequential
seeks). With a cut-out speaker, also look at every scene change: an outgoing card that is still fading after the cut
lands on the speaker's new position as a double exposure; end the exits before the cut.
