---
style: reacao
name: Reação (the speaker in front of the post)
family: fixed-style
best_for: reacting to a news item, a post, a launch page, a repository or a viral clip, from a raw take where the speaker only talks; commentary where the subject must be on screen the whole time
reference: technique study of creator Reels reacting to AI news (a translated X post with a large cutout in the corner; a GitHub explainer with a scrolled page, synced highlight boxes and header cards), Oct 2026; pilot built from a split-screen recording of a launch reaction
---
# Reação (the speaker in front of the post)

The raw take is only the speaker talking. The edit cuts him out (matte) and puts him **in front of the thing he is talking about**: the post, the article, the launch page, the repository, the screen recording of the product. The subject fills the frame behind him like a virtual green screen and is never a frozen wallpaper: it is pushed in on the line being discussed, scrolled to the next paragraph when the speech moves on, panned to the logo when he names the company, swapped for another source on the sentence that brings it, and marked (box, highlighter, underline, hand-drawn circle) on the exact word. A highlighter headline opens the video, white cards name the subject, captions run over the chest. The core metaphor: **he is standing in the news**.

## When to use / when not to

Use it when:
- the speech reacts to something the viewer must see (news, a post, a release, a page, a repository, a demo);
- the raw take is a talking head (phone, webcam, a split-screen export, a meeting tile with enough resolution) and the subject exists as a screenshot, a page that can be captured, a screen recording or a region of the same recording;
- the tone is commentary: surprise, analysis, a hot take, "look what they launched".

Avoid it when:
- there is no subject material (an empty backdrop is worse than a full-frame speaker: use `nativo` or `cinema`);
- the matte cannot hold (speaker tiny in the source, heavy motion blur, a background of the same colour as the clothes): test `qa/matte-sheet.jpg` first;
- the subject is private (DMs, personal profiles, client data) or copyrighted material that is not quoted for commentary;
- the viewer must see the subject and the speaker in separate frames for an A/B argument (`duelo`) or the headline must sit above the speaker (`manchete`).

## Signature moves

1. **Speaker cutout at the bottom, in front of the subject.** The face placed by state, the body fading out into a dark gradient by y ≈ 1660 (never a floating bust with a hard edge), a soft dark contact glow behind him so he separates from bright pages; the gradient also keeps the UI zone dark.
2. **The subject lives with the speech.** Each shot defines a *focus* (a point of the backdrop and how many source pixels fit across the frame); moves on the spoken words push in, scroll and pan; a slow drift keeps holds alive.
3. **Marks on the exact word.** Rounded box with a glow, highlighter band, underline drawn left to right, hand-drawn circle (stroke drawn in 0.5 s), each with an optional label pill whose text comes from the speech.
4. **Highlighter headline on frame 0.** Two or three lines, black on lime, what the speaker says in the hook, gone on the next sentence.
5. **Source switches on the sentence that brings them.** A swipe up (next post in a feed), a flash (a new page inside the same recording), a zoom; the credit chip at the top changes with them.
6. **Title cards naming the subject.** White rounded card at the top, small coloured kicker plus a two-tone title with the key words in the accent colour.
7. **Speaker states as jump cuts.** center, right, left, small (reveals the post), low, hero (hook/CTA), punch (rhetorical line), always hard cuts on a new phrase; punch-ins on the strongest line.
8. **Profile CTA.** The last frame of the speaker freezes, the backdrop dims, a profile card with the handle comes in and the button flips Follow → Following. When the speaker already said the CTA, it repeats his words; `"kind": "none"` ends with the speech.

## Frame and layout

```
y 0–270      atmosphere (backdrop only; the shade keeps the top readable)
y 280–326    source credit chip (site / profile), top right, for ~2.8 s after each source arrives
y 346–620    highlighter headline (hook, y adjustable) or title card
y 280–1000   the subject's focus area (anchor_y 560–820 for the point being discussed)
y ~1000–1660 speaker (hair top ≈ 1000 in center, ≈ 1030 right/left, ≈ 1220 small); body fades out by y 1660
y ≈ 1508     captions under the chin (caption_y; check that they never cover the mouth)
y > 1600     no information (speaker chest + dark gradient)
```

- Speaker states place the median face of the take at a target point (`reacaokit.SPEAKER_STATES`, size 1.0 = the camera as wide as the frame): `center` (0.95, face at 540/1320), `right`/`left` (0.88, 720 or 360/1340), `small` (0.66, 800/1450), `low` (0.85, 600/1430), `hero` (1.12, 540/1270), `punch` (1.32, 540/1230). The camera bottom never sits above y 1600 and fades out (mask) into the dark gradient, so a close-up take never floats. Override with `"speaker_states": {"name": [size, face_x, face_y]}`.
- The backdrop focus is `[cx, cy, w]` in the backdrop's own pixels, shown at `(540, anchor_y)`. The backdrop always covers the width and the top of the frame and reaches `min_bottom` (default 1300, the area of the head); a page taller than the frame covers it entirely and is clamped while it scrolls. A landscape recording (16:9) is therefore zoomed at least to that height: `w` is a wish. Lower `min_bottom` per shot to show more width (the band under it is the blurred, darkened copy of the same source behind the speaker), raise `max_top` to bring the first lines of a page below the platform UI. The bottom 160 source px of a backdrop fade into that copy.
- `heditor produce` writes `qa/marks.json` (screen rectangle of every mark when it appears) and prints a warning for a mark that touches the frame sides, sits above y 200 or is more than 25 % behind the speaker's head (head read from the matte). Fix every warning before the previews.
- Never park the point being discussed behind the head: use `anchor_y` ≤ 820, move the speaker to `small` or to the other side, or scroll.

## Palette and typography

| Role | Value |
|---|---|
| Highlighter headline | black `#0b0b0f` on lime `#d8ff3e` (beats `highlight`) |
| Accent (title words, CTA button) | brand accent (beats `accent`), e.g. `#2f6bff` |
| Marks | `#ffd84d` by default (per mark `color`); glow in the same colour |
| Credit chip | white on `rgba(11,11,15,.72)`, red live dot |
| Title card | `#ffffff`, text `#0b0b0f`, kicker in the accent |
| Captions | white Geist 900 with a 12 px black stroke, active word `#ffd84d` |

Fonts (kit): **Geist** 900 for the headline, titles and captions; **Inter** 700–800 for the credit chip, kickers and the CTA text.

## Caption system

Sentence case, source punctuation, 1–3 words (≤ 16 characters), Geist 900 white with a 12 px black stroke (`paint-order: stroke fill`), 0.1 em extra margin per word (the stroke eats the spaces) and a soft shadow, active word `#ffd84d` (≥ 4.5:1 against the stroke), hard swap per phrase with a 0.12 s pop, at `caption_y` (default 1508, under the chin). On a bright page the stroke carries the contrast; check enlarged crops at the brightest backdrop.

## Scene grammar

Generic example: a speaker reacting to a launch shown in a screen recording.

| Beat | Backdrop | Speaker | What happens |
|---|---|---|---|
| Hook | the launch page, pushed in on the hero | center | Highlighter headline on frame 0, credit chip "site". |
| Name | push-in on the product name | center | Box around the name with its label. |
| Company | pan to the logo | center | Hand-drawn circle on the logo. |
| Feature | the feature page (flash) | right | Title card naming the feature; box on the player when he says what it does. |
| Mechanism | scroll to the controls | small | Box on the controls on the verb; circle on one option. |
| Detail | scroll to the line that proves it | right | Underline drawn under the line with the spoken label. |
| Peak | push-in on the result | center | Punch-in on the strongest line. |
| Opinion | the result page (flash) | center → hero | Title card with his verdict in his words. |
| CTA | dimmed | frozen last frame | Profile card, Follow → Following. |

## Backdrop sources

| Source | How | Notes |
|---|---|---|
| Screenshot / post exported by the user | `"kind": "image", "src": "gen/post.png"` | Best for X/Instagram/LinkedIn posts (login walls block captures). Ask for a phone screenshot at full resolution. |
| A public page | `heditor capture <url> gen/page.png [--dark] [--desktop] [--viewport]` | Mobile viewport 430 × 932 @2x (860 px wide) by default, full page for scrolling, lazy images walked, cookie walls dismissed. Look at it: error pages and bot walls happen. |
| The subject inside the raw recording | `"kind": "region", "crop": "crop=w:h:x:y"` (or `heditor region <work> <name> <crop>`) | Split-screen exports, screen shares, a webcam recording with the page next to it: the region is cut with the same EDL as the camera, frame for frame. Crop away burned captions. |
| A screen recording or launch clip | `"kind": "clip", "src": "gen/rec.mp4", "media_start": 0` | Plays from its first shot onwards, muted. |

Read box coordinates on a still with a grid (`ffmpeg -vf drawgrid=w=100:h=100`) and write them in the backdrop's pixels.

## Transitions and motion vocabulary

- Focus moves: `power2.inOut`, 0.7–0.9 s, starting on the word; drift 3 % over a hold (`"drift": 0`, off).
- Source switch: swipe up 0.34 s `power3.out` (old page leaves upwards), flash 0.16 s for a new page inside the same recording, zoom 1.14 → 1 in 0.3 s.
- Marks: box `scale .9 → 1` with `back.out`, 0.24 s; highlighter `scaleX 0 → 1`, 0.34 s; underline 0.32 s; circle stroke 0.5 s; label 0.12 s later; out 0.2 s on `until`.
- Headline lines pop with a 0.07 s stagger on frame 0; title cards drop 22 px in 0.26 s.
- Speaker: hard cuts between states on a phrase start; punch-in instant, back in 0.18 s.

## Sound design

| Action | Category | gain_db | length |
|---|---|---|---|
| Headline on frame 0 | `pop` | −24 | 0.25 |
| Swipe / new source | `swipe` / `whoosh` | −24 | 0.4 |
| Box | `click` | −27 | 0.15 |
| Circle / underline / highlighter | `pen_write` | −27 | 0.45 |
| Title card | `pop` | −26 | 0.2 |
| Punch-in | `bass_impact` | −27 | 0.4 |
| CTA | `whoosh`, `click`, `success_chime` | −22 / −16 / −20 | |

**Music:** `music:187` (Mountains, hopeful electronic) for launches and "look at this", `music:82` (Keeping Fit, quirky tech groove) for a light reaction, `music:293` (Lord Knows, serious trap) for a hot take, `music:597` (Vertigo) for a worrying news item. Mix profile `voice` (organic reaction); the subject's own audio stays muted.

## CTA design inside the style

The speaker's last frame stays on screen (`speaker-last.png`, moved to the `cta.speaker` state, default `center`) while the backdrop holds its last frame dimmed and a profile card arrives above his head: logo, brand name, handle, one line from the speech, a button that flips Follow → Following with a click. With `"cta": {"kind": "none"}` the video ends with the speech (when he already said it and the post should be the last image).

## Implementation notes

- Reference build: `heditor new <work> <video> --style reacao` seeds `build.py`; write `beats.json` (format at the top of the build) and run `heditor produce <work> reacao 0`.
- `reacaokit.speaker_cutout` builds `camera-hd.mp4` at the camera's own size and `camera-alpha.webm` (matte at 720 px, merged with the full-resolution RGB; accessories dropped so a mic arm does not stay). Prefer a source where the speaker is at least ~900 px wide.
- `reacaokit.region_clip` re-cuts the EDL from another region of the source; `fill_layer` makes the blurred cover copy; `capture` screenshots a page; `freeze_alpha` keeps the last speaker frame for the CTA.
- Marks are drawn inside the backdrop's own coordinate system, so they move with every push-in and scroll; their stroke width is corrected for the zoom at the moment they appear.
- Render cost: one alpha video plus one or two backdrop videos (and their blurred fills); budget like `camadas`. The cutout (matte at 720 px + VP9 alpha at ≤ 1080 px) takes ~1/3 real time for the matte plus ~5 min of encode for 66 s on 4 cores; each stage is cached with its parameters. A 1440 px alpha made the render Chrome crash mid-render on a 4-core/8 GB host: keep `alpha_width` at 1080 and raise `PRODUCER_PUPPETEER_PROTOCOL_TIMEOUT_MS` for long cuts.

## Pitfalls

- **Point behind the head.** The most common defect: a box or the sentence being discussed sits at y 1000–1500 and the head covers it. Read `qa/marks.json`, then the previews; move the focus up (`anchor_y`), lower `min_bottom`, or move the speaker to `small` or the other side.
- **Empty bands.** A landscape recording fitted to the width leaves black bands above and below; the view clamp prevents it (cover width + top + `min_bottom`). Keep `max_top` for the first lines of a page only.
- **Marks at the frame sides.** A page wider than the frame is cropped; a box around the whole player or a full-width line is cut at the sides. Inset the rect or lower `min_bottom` (less zoom); labels are pushed 40 px inside automatically.
- **Credit chip against cards.** The chip lives top right for `credit_hold` seconds after each source; do not open a title card or a top mark in the same seconds.
- **Burned captions in the source.** Split-screen exports often have captions on the seam: crop them out of both the camera and the region.
- **Login walls and bot walls.** X, Instagram and LinkedIn rarely capture; ask for a screenshot. Some sites return an error page to headless browsers.
- **Private data in the subject.** Blur or crop handles, faces, emails and numbers of private people; public figures in a public post are fine for commentary.
- **Claims.** Titles and labels repeat what the speaker says; never add numbers or claims the speech does not make. Numbers inside the screenshot belong to the source and stay as they are.
- **Matte edges.** Fast hands blur into semi-transparent smears; dark clothes against a dark chair lose the edge. Read `qa/matte-sheet.jpg` and the previews at gesture peaks.

## Variations

- **Single post (corner cutout):** one screenshot full-bleed, the speaker in `right` the whole time, only the headline and two marks; the closest to the reference Reels.
- **Feed:** several posts in a row, each arriving with a swipe up on its sentence, the credit chip naming each profile.
- **Repository explainer:** a full-page capture scrolled section by section, title cards per section, boxes on the folders as they are named.
- **Launch demo:** the subject is a screen recording (region or clip), flashes on page changes, the speaker small while the demo plays.
