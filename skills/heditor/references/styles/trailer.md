---
style: trailer
name: Trailer (movie trailer)
family: fixed-style
best_for: launches, events, campaigns and announcements with a date to reveal; superlatives the speaker says himself ("the biggest", "historic"), lists of what is coming, a promise to reveal everything on a given day; paid-traffic ads with a "Learn more" CTA
reference: produced by the PycodeBR team with heditor, Oct 2026 (an ~80 s lead-capture ad for a launch event; v2 after a measured study of real suspense and launch trailers)
---
# Trailer (movie trailer)

A suspense/launch trailer built around the speaker. **Silence, light and timing** create the impact, not the amount
of graphics. The edit alternates hard cuts between the graded speaker and black, with real pauses inserted in the
speech for the beats, words that live **in the room** (on the wall behind the speaker, revealed by light, on a real
object of the set), letter-by-letter titles on black, and a score built in layers: suspense → crescendo → dense drums
→ a silent turn → final act → smash to silence → climax → poster.

## When to use / when not to

Use it when the speech builds to a reveal: launches, events, "on day X I will show you everything", spoken
superlatives, a list of what is coming (it becomes the montage), ads whose payoff is a date.

Do not use it for step-by-step explanations (black beats interrupt the reasoning), calm stories without a reveal
(use `documentario`), speech without silences between sentences (the beats need real valleys), or Reels under ~25 s.

## Numbers measured on real trailers (use them)

Two suspense film trailers and three product reveals (cuts, blackdetect, silencedetect, energy curves):
- **Text cards**: 1–3 words last 2.5–3 s, longer lines 3.5–4.5 s, the main title and the date ~4 s; hold ≥ 1.5 s after
  the last letter is legible. Montage items are the only exception.
- **Pure black breaths** 0.3–0.6 s, at most one every 8–10 s. **Silence before hits** in three tiers: accent
  0.4–0.8 s, chapter 1.0–1.7 s, one main drop 2–4.5 s. The dip sits ≥ 30 dB under the hit.
- **The hit lands on the first frame of the card** (0–2 frames). Swells and risers last 0.3–0.5 s and end exactly on it.
  Big impacts every 5–8 s in acts I–II; small accents (ticks, clicks) every 1.7–2.5 s; hits every 1.0–1.5 s in the
  final build; never two big hits < 0.7 s apart.
- **One smash to silence** near the end, on the strongest line: the music drops ≥ 25 dB in 0.1 s while the picture
  keeps running, ~1.5 s of voice alone, a 0.2–0.3 s riser, then a hard cut to black with the biggest hit.
- **Final build** of 15–18 s where cuts go from one every 2.5–3 s to one every ~0.7 s, ending on a hard cut.
  **Ending**: the poster enters on a hit that rings out 2.5–4 s; no new music after it.
- **Mix**: -14 LUFS, true peak ≤ -1 dBTP, ≥ 8 % of the runtime under -40 dBFS, score 10–15 dB under the voice
  with the hits on top.

## Signature moves

1. **Frame 0 on the face**, dark (an overlay that lifts in ~1.4 s), small wide-tracked "BRAND PRESENTS", the first
   caption already on screen; a low drone and a deep clock under it.
2. **Smash to black** after the first half of the hook line; the second half is spoken over black and spelled letter
   by letter (title-mode captions).
3. **Title after 1.0–1.2 s of near-silence**: impact + horn (braam) + deep drum on the same frame, the name spelled
   letter by letter (0.08–0.1 s per letter), LED glow, light streak; it then **survives onto the wall** behind the
   speaker as the next line starts.
4. **Facts on the wall**: years, numbers and key words appear as light on the back wall above the speaker's head, under
   his matte, while he says them.
5. **Montage**: "there will be X" lines on the wall; after each item a 0.35–0.45 s black beat with a drum hit where the
   item survives on black; a long list spoken over a darkened B&W face raised to the top, the items stacked below the chin.
6. **The turn**: smash to silence, black, two heartbeat pulses of LED light, then the most personal line in B&W with a
   slow push.
7. **Lights on** into the final act: the picture comes up from black in ~0.45 s on an impact + braam that peak just
   before the first word.
8. **A real object of the set as the hero device** (here a flip calendar showing the date): a 4K insert with rack focus,
   a mechanical click on the spoken number, the date lettering in the pause.
9. **Climax**: a continuous push-in (to ~1.4) while the score is cut away, a 0.3 s riser in the black, the biggest hit
   (impact + deep drum + thunder, an apocalypse horn swelling after it), the climax word spelled.
10. **Poster** on a hit: logo, title spelled, a thin gold rule, date, CTA button, one instruction line.

## Frame and layout (9:16, ad safe area)

- Letterbox bars 190 px top and bottom, always on. Camera full bleed, origin on the median face.
- **Wall text lives inside the camera rig** (`#camzoom`), between the camera video and the speaker matte video, so it
  sticks to the wall when the camera moves. Moving the picture therefore moves the text too: to put words above the
  head, place the text **higher in rig coordinates** (e.g. `top: 200px`) and move the picture down (`y: +80`) for those
  moments. On screen the band then lands just under the top bar while the head (measure its top on the matte alpha
  over the cut) stays below it. Keep the framing static (scale 1.0–1.02) while words are on the wall.
- Black titles centred between y 520 and 1000; caption band y 1046–1150; never text over the face (raise the picture
  with `y: -200` when lines must stack under the chin). CTA window `inset(280px 100px 1140px 100px)` with the camera at
  scale 0.82 (check it still covers the window: `547·(1−s) ≤ 100`).

## Typography

- One geometric sans (Geist, kit font) in caps, tracking 0.3–0.42 em, off-white `#ECEAF2` with a purple LED glow
  (`text-shadow: 0 0 30px rgba(150,110,255,.55)`); small secondary lines at 35–45 % size, 0.5–0.6 em tracking.
  No serif titles, no boxes or plates behind titles, no drop shadows, no glitch as the main device.
- **Wall text**: `mix-blend-mode: screen`, lavender `#E2DBFF`, 0.4 px blur, glow; the main word on one line with a small
  label inline before it (≥ 0.46 em).
- **Letter-by-letter**: one `inline-block` span per letter with the tracking as `margin-right` on each span and
  `letter-spacing: 0` on the parent (CSS letter-spacing is applied inside *and* between inline-blocks: double
  tracking, the line overflows); `text-indent` equal to the tracking keeps it centred.
- **Fit by measuring in the browser**: Chrome renders Geist ~25 % wider than a Pillow estimate. After writing the page,
  measure every title with Playwright (`Range.getClientRects` of its contents) and scale down anything wider than
  860 px (900 for wall bands); repeat once.

## Captions

Geist 700 caps on a translucent ink plate, the active word ink on a **white** pill (a light-grey pill read as muddy).
When the lettering shows exactly the spoken words (the hook half on black, the montage lines, spelled items), those
caption groups are not rendered in the band (`plan["captions_title_mode"]`); force caption breaks at the first word of
each lettering line. Transcribe the assembled voice **per speech run** (windows between silences ≥ 0.18 s): whole-cut
ASR puts the first word after an inserted pause inside the silence. A per-run window can merge two short words ("de IA"
→ one token): compare its text with a per-block transcription and split such tokens back.

## Grade

Cool steel, no yellow: neutralise the magenta/purple spill and rotate it toward indigo, 7000 K at 50 %, contrast ~1.3,
saturation ~0.76, neutral blacks with a 1.5 % floor, vignette. Compare 3–4 grades on frames from three moments with
vision before choosing and check that a black shirt does not read navy. Grade the source takes once so camera, matte,
inserts and the B&W variant share it. A warm grade (5500 K + warm highlights) was rejected as yellowish and amateur.

## Speaker matte

Run `dk.person_matte` on each graded **source take** (1080×1920 copy), not on the cut, and cut the alpha WebM with the
same frame ranges as the camera in the prepare (pauses = transparent frames): the matte never has to be recomputed when
the pauses change. Clamp low/high alpha (`lut=a='if(lt(val,46),0,if(gt(val,214),255,…))'`) to remove faint shelf
ghosts; keep wall words above chest height where the matte is solid; show the matte layer only while words are on the wall.

## Sound design

- **Score in layers** (Mixkit Free License), one track per act: a slow suspense bed (`614` Silent Descent), a crescendo
  for act II (`1011` Suffocation from ~4 s: -28 → -16 dB in 12 s), dense trailer drums for the montage (`678` Epical
  Drums 03 from ~1.9 s), silence for the turn, `686` Epical Drums 06 from its drop (28 s) for the final act and again
  from a dense section for the last CTA; cut the music to silence for the climactic line.
- **Cinematic stems** (Mixkit SFX, downloaded by id): impacts `780`/`781` (peak 0.18 s), trailer drums `551`/`565`/`546`,
  deep drum `552` (peak 0.47 s), braam-like horns `2291` (immediate) and `724` (peak 1.66 s: start it after the hit so
  it swells after), thunder `1286`, bell `619`, suspense swell `786` (peak 3.87 s: cut the last 1.3 s of the build into
  a file so it fits a pause), fast riser `792`, deep whoosh `1143`, stutter `787`, drones `1177`/`646`, deep heartbeat
  `498`, deep clock `1070`, mechanical click `1384`. Profile every candidate (peak time, attack, tail, low-band share)
  before placing it: nobody listens.
- **Placement rule**: every hit starts after the last word and its tail ends before the next line (trim `length`); a
  sound whose peak comes late (logo intros, horns, swells) is scheduled at `hit - peak` only if that start is silent,
  otherwise pick a fast-attack sound.
- **Louder bed**: `plan["mix"] = "presence"` (since 2.6.0 the same values the approved trailer used: music −15 dB,
  p95 −7 dB, < 30 % within 10 dB, ducks .62/.35/.6, SFX offset −4; read by `rk.mix` and the tests), and
  `plan["duck_open"]` = the pauses, so hits and swells land at full level. Inspect the 400 ms windows that still break
  the gate and fix the sound causing them (usually a tail running into the next line).

## Dramatic pauses

`prepare_cut` accepts `("PAUSE", seconds, "key")` blocks (digital silence + black frames, listed in `edl["pauses"]`;
`gaps`/`test` count only the silence around them). Put them after complete sentences on real valleys (RMS map at
-50 dBFS); a short dip inside a word (the occlusion of a "p") is not a boundary.

**In paid ads, keep the first 15 s talking.** Measured on running ads: trailer cuts with pauses, blacks and slow cards
in the first 15 s (70–75 % voice, ~25 words) held about half as well as cuts with near-continuous speech in the same
window (≥ 90 % voice, ≥ 38 words). Open with the title building over the speech and a card overlaid on the speaker
instead of a silent black card; save the dramatic pauses for the turn, the date and the climax after 15 s. Check
`first_15s` in `qa/final-verification.json`.

## CTA

"LEARN MORE ›" pill on the spoken words, tap ring, bouncing chevrons, then a chip for the destination; a second CTA
shows a checklist of the spoken steps. Poster ≥ 4 s. `test_duration_and_cta` expects the follow card with the handle;
with a "Learn more" CTA that failure is expected and documented.

## Pitfalls found in production

- v1 failed review: serif gold titles with plates, synthesised braams, fact cards of 0.33–0.5 s, a warm grade and music
  21.5 dB under the voice read as amateur and dull.
- Card tweens longer than their window turned labels back on after the cut: clamp every tween to its window.
- Contiguous overlay windows (black, dim, B&W) toggled off/on at nearly the same instant flicker or stay off: merge them.
- Wall words hidden by the head: the band was in the same rig as the picture (see Frame and layout).
- Hit tails (title, montage entry, lights on, date, climax) ran into the next sentence and made the auto-calibration
  lower the music by 6 dB.

## Variations

Steel-blue thriller (cyan LED) · warm epic (amber, slower pushes, choir swells) · teaser ≤ 30 s (hook, title, one fact,
date, poster) · another hero object of the set (a clock, a notebook, a monitor) instead of the calendar.
