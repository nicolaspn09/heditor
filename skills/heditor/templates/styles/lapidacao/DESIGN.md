# DESIGN — <cut> · style `lapidacao`

Read `references/styles/lapidacao.md` first. A style is a language, not a template: rebuild every act from this speech.

## Source and cut
- Source, framing, mirrored? (selfie footage is often mirrored: hflip before prepare)
- Hook block → `("PAUSE", 0.5, "p_apagao")` → the rest. Cuts and why (repetitions, false starts, forbidden claims).
- Joined takes: list each junction and how it was verified (energy of the assembled voice, not ASR).

## The transformation in the speech
- Raw material (what is "raw" here): …
- The refining step (the cut): …
- The result and its named parts (the gem's facets): …
- "Only then" the tool/machine and how its work is reviewed (the loupe): …
- Steps said vs unsaid (tray: shown niches vs locked ones): …
- Qualities to certify (one per spoken word): …
- Offer (case), warning (slam), condition/date (tag), group (rope), CTA: …

## beats.json (event → spoken word)
| act | keys | words | on-screen text (exactly as spoken) |
|---|---|---|---|
| hook | tab, freeze, cursor, close | | hook title, window title, tab |
| plaques | plaque1, plaque2, plaque_sheen, glyph1, cut1, glyph2, cut2 | | |
| raw | step1, sheet, caret, line1..line5, lines_end, compact, land | | sheet lines, raw label |
| cut | step2, riser, laser, shards, flash, title, subtitle, doc, row2..row4, rows_dim | | gem title, sub, rows |
| machine | machine, machine_on, pill, tasks, code, loupe, stamp | | tasks, stamp |
| tray | tray, tray_in, tray_title, niches, tray_sheen | | tray title, niches |
| certificate | cert, cert1..cert3, cert_seal | | rows |
| case | case, case_open, case_gem, case_glow, case_seal, forever, flicker, slam | | seal, forever |
| condition | tag, flip, tag_time, tag_note, rope, vip_plate, vip_sheen | | tag texts, group plate |
| CTA | cta, button, rope_open, bell, toggle, envelope, envelope_seal, fin, fin_line, final_punch | | button, envelope, final date |

Floor words per act: …  Numbers on screen and where they were spoken: …

## Objects (`gen/`)
raw_stone.png, cut_diamond.png (edit of the stone), box_closed.png, box_open.png (edit of the closed box), rope.png;
prompts in `lapidacao_kit.OBJECT_PROMPTS`. No text, no logos, never the speaker. Record the model and date.

## Score and mix
Main track and its energy jump (aligned to `flash`), CTA track, licences; `plan["mix"]` louder than the kit default;
asr-check medium result.

## Risks
Matte (chair, black clothes, fast hands), face clearance in each layout, numbers, claims, safe area, render time.
