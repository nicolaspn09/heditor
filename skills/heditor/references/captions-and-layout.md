# Captions, layout and camera

## Other canvases

The numbers below are for 9:16 Reels. Every format profile (`heditor formats`: 16:9, 16:9 4K, 1:1, 4:5) has its own
safe area, caption zone and screen/camera layouts (`pip`, `screen` with zoom, `speaker`, `side`) in
`scripts/reelkit/formats.py`; `long-form.md` documents them. In 16:9 captions are subtitles (≤ 2 lines × 42
characters at ~50 px, y 880-1020), not kinetic words; the active-word contrast rule below applies to every canvas
(style packs are tested for ≥ 4.5:1).

## Safe zones (1080×1920)
- Top 0–270 px (14 %): no text, face, logo or key graphic (platform UI). Anton/condensed titles with accents rise above their line box: start titles at ≥ 300 px and verify with the pixel check (first row with luma > 150 on > 8 px must be ≥ 270).
- Bottom ~350 px (y > 1570): only atmosphere; the platform caption/buttons live there.
- Right edge ~120 px between y 1000–1700: like/comment/share buttons; no critical info.
- Face never covered by graphics or captions. Track it (`rk.track_faces`) and place graphics on the opposite side.

## Captions
- Every spoken word, in order, synced (word or phrase level). `plan["captions"]` must match exactly what appears; tests compare it with `words-reviewed.json`.
- Corrections of spelling/brand names live in `words-reviewed.json` (timings untouched). Profanity masked on screen only.
- Size on a phone: ≥ 60 px cap height for phrase captions (Anton 84–96 px), ≥ 46 px for interface-style captions (chat, code, radio).
- Active-word contrast (mandatory): black text on light yellow `#ffd84d` or white, or white text on a saturated dark colour. Never dark text on a mid-tone pill, and never a dark outline around dark letters. In the kit's `pill` mode the outline takes the pill colour.
- Group 1–3 words (≤ 17 chars) for kinetic captions; full phrases for subtitle-like systems; never more than 2 lines.
- World-native caption systems that worked: RPG dialog box with ▼ cursor, code comments typed in an editor, radio transmission in a mono font with amber active word, chat bubbles that grow word by word, documentary subtitles in serif with underlined active word, giant karaoke with one word at a time, film subtitles in lowercase with a blinking keyword.

## Camera treatments
The source webcam is often small (e.g. 320×238 px in meeting recordings). Upscale to ~960 px wide (Lanczos + light unsharp) and never stretch it full height. Ideas: card, circle bubble, monitor/CRT inside a scene, game character window, CCTV feed, video-call window, tilted editorial rectangle with hard shadow, letterbox strip, split screen (two grades of the same feed), clones grid (copies with different grades), PiP that shrinks for a typographic finale, freeze-frame. Pause cuts become shot changes with the jump-cut zoom (1.0 ↔ 1.075 around the face); add a 1–2 % breathing zoom elsewhere.

### Presenter cutout (alpha-matted speaker)
Several styles place the speaker *inside* the world (in front of a stage screen, on a shop threshold, behind a counter) instead of in a card. That needs an alpha-matted copy of the camera: a WebM VP9 with alpha (`yuva420p`, `alpha_mode=1`) played over the scene. Since 1.5.0 the kit ships one: `heditor matte <work>` (depthkit, MediaPipe multiclass segmenter + guided filter, Apache-2.0) writes `camera-alpha.webm` with the camera RGB untouched; see `depth-and-3d.md`. For harder sources, external matting tools also worked (record their licence in DESIGN.md): Robust Video Matting (MobileNetV3, GPL-3.0) gated by the MediaPipe selfie segmenter (Apache-2.0) to drop furniture the matte keeps; Apple Vision person segmentation (`.accurate`, macOS only) plus a clean background plate. Rules learned in production:
- Change only the alpha. Keep the camera RGB untouched (no grade inside the matte) unless the style asks for one; despill only a thin band (≤ 8 px) at the alpha edge.
- Test the matte on a short window with vision before committing to it. Dark clothing against a dark chair, glasses bridges, fast hands and motion blur are the usual failures; fill small holes, add an opaque floor on the face, and hide residues with a dark disc, a velvet arch or a soft shadow behind the speaker.
- Dissolve the frame edges and the body base with a CSS mask gradient so the source frame border never shows.
- If the edge still fails, fall back to a well-designed card or window inside the world (the `album` style was born from that fallback).

## Paid-ad variant ("Learn more" CTA)
- Mix: `plan["mix"] = "presence"` (music ~15 dB under the voice, presence floor, asr-check required; `sound-design.md`).
Ads that run with the platform's own CTA button (Meta Reels/Stories "Learn more" / "Saiba mais") need a different safe area: the ad UI covers more of the lower screen than an organic Reel.
- Captions sit higher: one line (`nowrap`), ≤ 800 px wide, inside y 1046–1150, font size fitted to the line length (`--fs`). Nothing critical below y 1152; that area is atmosphere only (floor, sea, audience silhouettes, body fading out).
- Titles still start at y ≥ 300; the face stays clear of every graphic.
- The CTA is the action, not Follow: a large white "LEARN MORE ›" button (in the user's language) tapped by a finger on the spoken word, down chevrons and a "TAP LEARN MORE" line after the last caption, then a 4–4.5 s end card with only the brand mark and the button. `heditor test` fails `test_duration_and_cta` (handle + Follow/Following) by design: document it, never work around it.
- Truth rules get stricter: only what the recorded speech says reaches the screen (if the script and the recording differ, the recording wins); no prices, discounts, remaining slots, countdowns or invented scarcity. The advertiser's own product pages or screens may appear as proof, cropped so no price or personal data is legible.

## Layout patterns
- Hero: camera large between y≈500 and 1200, captions band below (y 1222–1472), headline above (≥ 300).
- Top camera: camera small at the top (y≈280) and graphics in the centre (y 670–1200).
- World UI: the whole canvas is an interface (editor, chat, radar, game) and the camera is one element of it.
- Finale: camera PiP at the top, giant type in the centre for the key line.
