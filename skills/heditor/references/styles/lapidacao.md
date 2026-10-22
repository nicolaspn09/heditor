---
style: lapidacao
name: Lapidação (luxury jewellery commercial)
family: fixed-style
best_for: paid-traffic ads and launch invitations whose speech turns something raw into something valuable (a raw idea, draft or prompt refined into a precise result, "the first thing I do is not X", a process in named steps), followed by an offer revealed on a date to a private group; works with a "Learn more" CTA
reference: produced by the PycodeBR team with heditor, Oct 2026 (paid ad for a launch's VIP group); reference build in templates/styles/lapidacao/
---
# Lapidação (luxury jewellery commercial)

The Reel is a high-end jewellery commercial. It opens in the speaker's real room with a familiar tool on screen (a code editor writing by itself, a spreadsheet, any "where everyone starts"), a two-line curiosity title and a cursor that **closes** it; the room then goes dark on a declared pause and a cool spotlight finds the speaker alone in a black void, with dust in the beam. From there every step of the speech is an object under the light: the raw material (typed live on a plain sheet as the speaker lists it) is sucked into a **rough stone** that drops on the velvet; refining it is the **cut** (laser sweep, facets drawn, sparks and shards, a white flash) and the result is the **cut gem**, whose facets name the parts of the spoken result; the machine/tool comes in only after that, and a **jeweller's loupe** reviews its work line by line; a **display tray** shows the steps of the method with the unsaid ones locked; a **certificate** grades the result; the offer is a **jewellery case** that opens with the gem in its lit slot and **slams shut** on the warning ("but attention…"); the condition is a **sealed tag** with the spoken date; access is a **velvet rope** that parts when the button is tapped. The core metaphor: **the value is in the cut, not in the stone**.

## When to use / when not to

Use it when the speech:
- turns something raw into something refined (draft → document, idea → system, rough → precise), ideally with the word *bruto*/raw/draft in it;
- describes a process in steps with "only then" a tool or AI;
- closes with an offer or condition revealed later (date, live, class) to a private group (VIP, list, waitlist);
- runs as an ad with "Learn more" or as a premium launch invitation.

Avoid it when:
- there is no transformation (a plain announcement, a list of features, a story); prefer `stories`, `keynote` or `trailer`;
- the speech is casual or humorous (the world is slow and luxurious);
- the batch already has a noir/black-and-gold world (`cassino-de-precisao`, `trailer` on black): change the palette accent or the objects;
- the speaker's matte fails badly on the source (light background with light clothes): the world needs the cutout on black.

## Signature moves

1. **Frame 0 already busy**: the speaker's real room, a two-line title with an ellipsis that blinks ("THE FIRST THING I DO…"), a dark editor window in perspective that keeps writing code line by line, and the brand engraved on the floor area.
2. **The tool is closed**: on the spoken "not open the editor", a cursor travels to the red dot and clicks; the window squeezes into a CRT line and a dot.
3. **Blackout**: a declared `PAUSE` of ~0.5 s (black frames + digital silence + a heavy light switch); the spotlight snaps on with a flicker, dust in the beam, the room is gone, the speaker is cut out under the light.
4. **Two plaques** flanking the head for "the first two steps", each with an icon that is **cut by a line of light** on "no line of code / no technical step".
5. **Live raw sheet**: a plain text-editor sheet in perspective types each item exactly when it is said, then fills with grey lines.
6. **Compaction**: all the text is sucked into the centre and becomes a dull rough stone that drops on the velvet with a sub thump (engraved label below it).
7. **The cut**: a laser line sweeps the stone, facets are drawn with a bright stroke, sparks and shards fly; a white flash reveals the brilliant; the result's name is engraved big, its long form small.
8. **Facet sections**: the gem rises and its parts light as a checklist on their words.
9. **Only then the machine**: the editor of the hook comes back (loop closed), with a pill for the AI/tool, tasks flying in from the gem badge, code generated line by line and a **jeweller's loupe** magnifying the code while each line gets a check; a stamp closes the step.
10. **"Just a summary"**: everything recedes into a display tray of N niches; the steps already shown carry the stone and the gem, the others are covered with velvet and a padlock (curiosity gap).
11. **Certificate** for the spoken qualities (one check per word, embossed seal).
12. **The case**: opens with the gem flying into the lit central slot; the campaign seal and "lifetime"/"forever" (∞ drawn) appear under it; on the warning the music cuts, the spot flickers and the case **slams shut**, sealed.
13. **Sealed tag** hanging from the seal: front with a padlock, flip to the spoken date, time and occasion.
14. **Velvet rope** with the group plate in front of the case; the white button appears on "learn more", a finger taps its end, the rope parts, a notification bell switches on, a sealed envelope promises more information.
15. **Floor words**: one big engraved word per act on the velvet floor (atmosphere below the ad UI), e.g. EDITOR → NO CODE → RAW PROMPT → PRD → AI → 5 STEPS → … → VIP GROUP.

## Frame and layout

- Canvas 1080×1920, 30 fps; paid-ad safe area: titles from y ≥ 300, captions in one line inside y 1046–1150, nothing critical below 1152 or outside x 80–1000; the bottom is atmosphere (velvet floor, pool of light, floor word).
- Speaker: `#prig` holds the full source frame (graded plate + alpha matte, same box). States from the median face centre (`lapidacao_kit.rig_states`): `full` (scale 0.78, face centred, hair at y ≈ 330), `right` (0.62, face x ≈ 740, objects in the left column x 80–560), `left` (0.62, face x ≈ 340, objects in the right column x 520–1000), `low` (0.50, face lower, tray in the top band y 300–565). Body and sides of the alpha fade with a mask (bottom 74–93 %, sides 10 %), so the source edges never show as hard lines.
- Columns: objects sit in the free column, ≥ 40 px from the head; nothing crosses the face (check the previews: plaques, editor and certificate are the tight spots).

## Palette and typography

- Void: radial `#0b0c10 → #050506 → #020203`; spot: cool white `rgba(220,232,255,.2)`; ink `#03090E`; champagne `#EDC580` (engraving gradient `#b8935a → #EDC580 → #fff7e4`), light champagne `#F3D79B` for the caption pill, cold white `#EEF3F7`.
- **No yellow cast on the speaker**: neutral-cool grade (`lapidacao_kit.GRADE`); the gold lives only in graphics and objects. Compare 3–4 grades by vision on a new source; the black t-shirt must stay black.
- Geist (OFL) only: engraved caps with wide tracking (0.32–0.5 em) and a slow sheen sweep; JetBrains Mono in the editor. No serif gold plates.

## Caption system

One line in the ad band (y 1046–1150, 840 px wide), Geist 800 upper case, size fitted to the line (`min(78, 800 / (0.66·n))`), white with a dark shadow; active word **black on light champagne `#F3D79B`** (≥ 11:1). Trailing punctuation is removed from the displayed words (not from the plan).

## Scene grammar (beats.json)

The reference build maps every event to a spoken word (`keys`), every on-screen text to the speech (`text`), one floor word per act (`floor`) and the music (`music`); format at the top of `templates/styles/lapidacao/build.py`. Acts, in order: hook (editor, close) → blackout + spotlight → plaques → raw sheet → stone → cut → gem + facets → machine + loupe → tray → certificate → case (open, seal, forever, slam) → tag (front, flip, date, time, occasion) → rope → CTA (button, rope opens, bell, envelope, date + link) → end card → campaign seal. Rename and reorder acts in the build when the speech needs it; never show a word or number the speaker did not say.

## Transitions and motion vocabulary

Layout moves with `expo.inOut` 0.6 s while the previous objects leave 0.2 s before and the new ones enter after; impacts in the gaps (stone landing with a small world shake, case slam with a bounce); the flash is ≤ 0.35 s; the loupe moves line by line (0.22 s) with its content magnified 1.7×; floor words fade in per act; the presenter breathes 2 % and alternates 1.0/1.035 at each EDL junction (face-centred).

## Sound design

- **Score**: the identity of the style is a score you notice. One driving track builds from the spotlight on and is aligned so its energy jump lands on the gem flash; silence on the blackout and on the warning; the same track low-passed under the condition; a second, powerful track for the CTA and end card (defaults: `music:126` "Trap Electro Vibes", breakdown 40–48 s with the kick entering at 48 s on the gem flash, and Mixkit m179 "Solitude"; both measured with a presence-band share ≥ 0.24). Mix profile `presence` (`rk.MIX_PROFILES`) with the reference edit's targets: `{"profile": "presence", "music_median_db": -15.5, "bed_p95_db": -9, "within_10db_pct": 9, "low_duck": .38, "sfx_duck": .7, "sfx_offset_db": -7}` (≈ −17 dB measured), `duck_open` on the blackout, silence sections declared as `"silence"` (the presence floor ignores them); profile the tracks with `heditor music` and always confirm with `asr-check` medium. Bass-only tracks disappear on phone speakers: choose tracks with mids and percussion.
- **SFX map** (Mixkit + synthesised in `lapidacao_kit.synth`): keyboard under the hook; click + CRT power-down on the close; heavy switch + sub on the blackout; spotlight clunk + shimmer; metal ticks on the plaques; glass hit on each cut icon; paper slide on the sheet; typing on the raw lines; vacuum on the compaction; deep impact + sub on the stone; laser + grinder on the cut; glass hit + crystal ting + sparkle on the flash; crystal ticks on the facets; power-up on the machine; clicks on the tasks; shutter + ticks on the loupe; staple on the stamp; lock clicks on the niches; paper + stamp on the certificate; latch + crystal on the case; trailer impact + shimmer on the campaign seal; case slam + lock on the warning; slow ticks under the condition; paper on the tag; velvet whooshes on every layout move; click + bell on the CTA.

## CTA design inside the style

The rope with the group plate in front of the sealed case; white button with the platform's words ("Learn more ›" in the user's language) on the spoken word, a finger tapping its right end (never over the label), chevrons down, the rope parting, the bell switching on and the envelope; end card ~4.3 s with the sealed case centred, the campaign title, the button and the one-line instruction; the last second is the campaign seal in the brand's identity. On a paid ad `test_duration_and_cta` fails by design (no handle/Follow): document it.

## Implementation notes

- `heditor new <work> <video> --style lapidacao` → `prepare.py` with a `("PAUSE", 0.5, "p_apagao")` block after the hook → `heditor prepare`/`words` → five object photos in `<work>/gen/` (prompts in `lapidacao_kit.OBJECT_PROMPTS`: no text, no logos, never the speaker's face) → `beats.json` → `heditor produce <work> lapidacao 0` → lint → previews → test → render → finalize → asr-check.
- The build computes the face median (`rk.track_faces`), the rig states, the graded plate and the matte (`lapidacao_kit.camera_and_matte`: multiclass matte at 720 px, levels clamped 38→0 / 197→255, static garbage mask around the head and below the shoulders, alpha merged with the full-resolution RGB); all rebuilt only when `camera-src.mp4` is newer.
- Object photos get soft elliptical alpha and a darker velvet (`lapidacao_kit.objects`); the raw stone is desaturated, flattened and frosted so the before/after reads.
- Render: ~4–7 min for 97 s on an M-series Mac with 4 workers (alpha video + many layers); the composition stays under the heavy-overlay limit (~31 elements).

## Pitfalls found in production

- **Matte background not zero**: the grey matte comes back from H.264 at ~10–12 (and room residues up to ~40), so the room ghosted through at 4–5 % alpha. Clamp the levels and multiply by a garbage mask; check the cutout over mid grey, not only over black.
- **Accessories class**: dropping class 5 of the multiclass segmenter removes the glasses frames; keep it and rely on the dark world for the chair.
- **Hard source edges**: scaled down, the source frame's sides cut the hands in the air; fade the sides of the alpha box.
- **A floor glow with a top edge** reads as a box: start the floor gradient transparent.
- **Floor words in perspective** got clipped at the sides; flat, fitted to 840 px, soft gradient fill.
- **The raw stone must look raw**: the generated stone looked cut already; process it to a dull grey version.
- **The cursor and the title**: keep the editor window below the hook title (they collided when the window tilted).
- **Loupe over the task list**: start the loupe path below the tasks; magnification offset uses the code box origin.
- **Splicing two takes of the same phrase**: the onset of the retake right after a repeated word (the brand name at the end of take 1 + "with access…" from the retake that also said the brand name) sounds like a repetition. Enter on the next word in a real valley and verify by the energy of the assembled voice: ASR inserts the expected word even over digital silence.
- **Score too low**: the kit default bed (−21.5 dB) with a bass-only track read as "no music". Even at −17 dB a track whose energy is almost all kick and bass (presence-band share ~0.05, e.g. a deep techno bed) leaves the first half of the video "without music" on a phone; the `presence` floor flags it (`music_gaps`). Measure the 500 Hz–6 kHz share before choosing and keep it ≥ ~0.2.

## Variations

- Other precious materials: watchmaking (raw movement → assembled calibre, loupe and certificate of chronometry), perfumery (raw notes → distilled essence), tailoring (fabric → fitted suit).
- Light version: a cream velvet atelier with ink-black objects (changes the palette and the camera treatment).
- Organic version: no CTA hardware (rope, button); the case opens on the final line and the floor word closes the video.
- Keep at least two of camera treatment, palette accent and transitions different from the last lapidação in the same batch.
