# Pre-production: recording plan and edit plan from scripts

Use when the user sends written scripts (paid ads, Reels, a batch of short videos) and asks for a **recording plan and an edit plan before recording**. The deliverable is a plan document plus a teleprompter file. Nothing is recorded, edited, uploaded or created in shared folders unless the user asks.

Good pre-production removes most editing problems before they exist: a gesture tied to a word gives the edit a visual cue, a locked tripod makes a matte or a screen projection possible, two seconds of silence between sentences give clean cut points, and a fact checked now avoids re-recording a sentence later.

## 1. Procedure

1. **Export the source.** A Google Doc shared by link exports without authentication: `curl -sL "https://docs.google.com/document/d/<ID>/export?format=txt" -o brief.txt`. Read it with `encoding="utf-8-sig"` and strip `\r`. Keep the export with its SHA-256 and cite the link and the local path in the plan.
2. **Read the campaign context.** Limits (prices, bonuses, product names, words that cannot appear together), the CTA destination, the campaign identity (palette, fonts) and the styles already used by other content that will run in the same period for the same audience.
3. **Measure the scripts with code, not by eye.** Separate speech from on-screen text notes and scene notes. Count words per video. Edited duration ≈ words ÷ speaker pace + 4–4.5 s of end card; measure the pace on a previous edit of the same speaker (last word end in `words-reviewed.json`; a fast, pause-trimmed ad pace is about 3.2 words/s). Compute the position (% of words) of the first mention of the brand, campaign and date: when it comes after ~2/3 of the speech, plan a discreet brand mark from frame 0 and a campaign tag that appears at the first spoken mention, so viewers who leave early still know what the ad is about.
4. **Inventory the set without asking.** Run vision on photos the user already sent and on contact sheets of previous edits (`qa/final-contact-sheet*.jpg`): background, screens, lights, props, microphone, clothing, framing. List only what the images show; do not assert room geometry they do not show.
5. **Check existing screen recordings before promising reuse.** `ffmpeg -i take.mp4 -vf "fps=12/<duration>,scale=480:-1,tile=4x3" -frames:v 1 sheet.jpg`, then ask vision what appears, which personal data is legible (names, e-mails, values) and what the footage does **not** prove (a code editor without an agent panel or a diff does not prove "code written by AI").
6. **Fact-check every number and study** at the primary source, including later updates, corrections or "out of date" notices from the same source. Propose a wording change that keeps the hook and the order of ideas, and a small on-screen source line, as decisions for the user. Superlatives and demo timings ("in 40 seconds") are also the user's call.
7. Write the **recording plan** (§2), the **teleprompter** (§3) and the **edit plan** (§4).
8. **Audit the document** (§5) and save it where the user keeps production notes.

## 2. Recording plan

- **At most two setups, ordered for a single change.** Setup A, work position: phone on a tripod where the webcam sits, behind the main monitor at eye level; the teleprompter at the top of that monitor, just under the lens, so the eye line stays near the lens; the computer within reach for demos. Setup B, desk as background: the chair turned away from the desk and the phone in the middle of the room, with the screens and props behind the shoulder; the monitor cannot be read there, so use a tablet under the lens or record sentence by sentence.
- **Phone settings:** main lens 1×, 4K 30 fps, HDR video off (HLG sources need a tone-mapping step before editing), exposure/focus lock on the face, do not disturb on, lavalier on the collar with a 5 s test listened to on headphones, 10 s of room tone per setup.
- **Frame wider than a selfie:** head to waist with the hands visible. The edit crops the speaker into the lower half of a split, into cards and into body cutouts; 4K leaves room for that.
- **Matte-friendly clothing:** dark clothing against a dark chair is the usual matte failure; wear a contrasting solid colour or sit forward so the backrest does not frame the shoulders.
- **One continuous take per video**, sentence by sentence, with 2 s of silence between sentences; after a mistake, restart the whole sentence; the hook twice, with different energy. On the spoken CTA ("learn more"), point down where the platform button sits, then hold 2 s of silence looking at the lens.
- **Tie every gesture or physical action to a word** of the speech: pointing "up here" in a split screen, counting steps on the fingers, closing a laptop lid on "close the editor". The edit fires the visual event on the gesture.
- **Locked tripod, no adjustment between takes,** for styles that need a matte or depth (`camadas`, cutouts) or that project content onto screens in the set; for projection, leave those monitors on a full-screen black image. Projection by fixed corners has not shipped as a kit function yet: keep a fallback (cutout in front of a drawn screen).
- **Screen and camera at the same time** for narrated demos, with a clap at the start for sync. A spoken time claim needs a visible timer; the screen may be sped up with the measured timer on it, the voice never, and the sentence follows the measured time.
- **Screen recordings:** do not disturb on, browser zoom 125–150 %, editor/terminal font ≥ 18 px, bookmarks bar hidden, slow cursor and 2 s per action; never show `.env` files, tokens, e-mails, phone numbers, customer or student names, revenue or prices.
- **Inserts:** 3–5 s each, phone in hand, two takes: the key prop, the lit set, hands on the keyboard, the phone filming the monitor with a finger on a line (more believable proof than a clean capture), a lid closing, a pen on paper.
- **Per-video recording sheet:** setup, gesture on the exact word, screens (T1, T2…) and inserts (I1, I2…), with which existing recordings are reused and what they must hide.

## 3. Teleprompter

Generate it **by script from the export**, never by retyping: only the spoken lines, cues in brackets *before* the sentence they belong to (gesture, pause, where to look), a cue before every line containing the CTA and a final silence cue. Verify by script that the spoken lines are identical to the source, in order, for every video.

## 4. Edit plan for a batch

- **One heditor style per video,** no repeats inside the batch and none of the styles used by content running at the same time for the same audience. Two videos on the same topic need worlds that do not resemble each other.
- **Choose by the structure of the speech:**

| Speech structure | Starting style |
|---|---|
| Short invitation with a date | `stories` in a home-made version (full-frame footage, plain story text boxes) |
| Launch with a superlative and a list of what is included | `keynote` |
| Products named one by one | `album` with the official covers |
| Study order or steps counted on the fingers | `game` |
| Fast list of things you can build | `camadas` |
| A system shown as proof | `predio-24h` |
| Code reviewed on screen | `bancada` |
| A bug demonstrated live | `thriller` |
| Two opposite numbers and a verdict | `tribunal` |
| A physical action that changes the video | `ruptura` with the camera as the metaphor |
| A direct question to the viewer | `auditorio` |

- **Batch table:** video, starting style, world, camera treatment, caption system and music (one distinct track per video from `assets/catalog.json`).
- **Per-video sheet:** world, hook on frame 0, the visual event sentence by sentence quoting the speech literally, CTA, and cautions (data to blur, screens that must come from the recording, fallback).
- **Paid-ad CTA:** the "learn more" button appears on the spoken word, with a tap and down chevrons; each world draws its own CTA and only the last second repeats the campaign tag.
- **On-screen text from the script** enters literally on its word; if the recorded speech changes, the screen follows the speech. A source line that is written but not spoken goes in only with the user's approval.
- **Edit order by dependency:** first the videos that need only the camera and can go live soonest; last the recorded demo and the ones waiting for a user decision. Optionally, a `nativo` version of one or two videos next to the creative edit measures what the edit adds; suggest it, do not decide it.
- **When the recordings arrive:** run `heditor triage` on every raw file before editing (reading pauses, retakes and
  asides to the editor are normal in teleprompter takes), and adapt each sheet to what was said: a step the speaker did
  not say appears locked without a name, a fact not said stays off screen, and the delivery lists what of the script
  was left out. Screens that were planned but not recorded come from recordings that already exist, projects run
  locally and captured, or public pages; generated images only for objects and atmosphere of the world, never as a
  system screen or a result.
- **New openings for videos already running** (hook tests): plan one opening per hypothesis (concrete proof on frame
  0, the first word is the object, the pain or the question, at most 12 words said before 3 s), record two energies of
  each in the same set and light as the body, and edit them with `hook-variants.md` so the body stays identical.

## 5. Document audit

- Extract every quoted fragment by script and check it against the normalized source (lowercase, punctuation removed, spaces collapsed). Anything that does not match is an on-screen label or a paraphrase: fix it or make it stop looking like a quote.
- Do not shorten quotes with omission ellipses; cite the whole sentence or two separate fragments.
- Run the language checks of the user's editorial rules (forbidden words, punctuation, accents) on the plan and the teleprompter, re-read after the last edit, then save.
