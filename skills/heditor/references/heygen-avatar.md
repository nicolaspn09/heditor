# AI avatar videos from HeyGen (optional)

heditor can take its source video from an AI avatar instead of a camera: the person's own HeyGen digital twin speaks
an approved script (or lip-syncs an audio file) and the result enters the normal workflow (`heditor new` → prepare →
words → DESIGN.md → build → QA → render). **This is optional.** Nothing else in heditor needs HeyGen, `setup.sh` does
not install it and `heditor doctor` only reports it as a warning.

heditor drives the official [HeyGen CLI](https://developers.heygen.com/cli) (`heygen`). The CLI owns the credential
(`~/.heygen/credentials`, mode 0600, or `HEYGEN_API_KEY`). heditor never reads, prints, stores or passes a key on a
command line.

## Connecting (the account owner does this, once)

```bash
heditor heygen connect            # interactive assistant (PT or EN, from brand.json "lang" or HEDITOR_LANG)
heditor heygen status             # connection, billing mode, plan, credits or wallet balance
heditor heygen disconnect         # removes the stored credential
```

The assistant installs the HeyGen CLI if it is missing (official installer, checksum verified, `~/.local/bin`), then
offers two ways to connect:

| Choice | Billing | When |
|---|---|---|
| HeyGen account (OAuth) | the **premium credits of the HeyGen subscription** | the person already pays for a HeyGen plan; HeyGen describes OAuth as suited to tests and low volume |
| API key | the **prepaid HeyGen API wallet** (USD, separate from the web plan) | batch production; the key is typed into the HeyGen CLI's hidden prompt |

On a desktop the OAuth choice opens the browser. On a server or over SSH (no display) heditor uses `--remote`: the
HeyGen CLI waits on a loopback port, heditor prints the authorize link, the person approves on any computer, the
browser lands on an error page at `http://127.0.0.1:<port>/oauth/callback?...`, and the person pastes that address
back. heditor checks port, path and `state` before delivering it to the waiting CLI; the PKCE verifier never leaves the
HeyGen CLI, so the pasted code is useless anywhere else. `--device` calls HeyGen's device-code login, which only works
when HeyGen enables it for the CLI (it answered `invalid_request` in October 2026).

Rules for agents:

- **Never run `connect` for the user** and never ask for a key, password or code in chat. If `heditor heygen status`
  exits 3, tell the user to run `heditor heygen connect` in their own terminal and wait. Without a terminal the
  command refuses and prints the commands to run.
- One credential at a time: logging in again replaces the previous one. `HEYGEN_API_KEY` in the environment always
  wins over a stored OAuth login; `status` warns about it.
- The HeyGen CLI sends anonymous usage telemetry linked to the account after login. `HEYGEN_NO_ANALYTICS=1` turns it
  off.

## Generating the source video

```bash
heditor heygen avatars                     # your looks: id, type, orientation, engines (v, iv, iii), default voice
heditor heygen voices                      # your cloned voices
heditor heygen glossaries                  # pronunciation glossaries (term -> respelling)
heditor avatar cortes/c01 --look <id> --script roteiro.txt --dry-run   # plan, estimate and request; spends nothing
heditor avatar cortes/c01 --look <id> --script roteiro.txt              # asks for confirmation, then renders
heditor new cortes/c01 cortes/c01/source/avatar-<video_id>.mp4          # then the normal workflow
```

Inputs (exactly one): `--script FILE`, `--text "..."` (the look's default voice, or `--voice ID`) or `--audio FILE`
(mp3/wav lip-synced as is; for example the person's own recording, so only the picture is synthetic).

Options: `--glossary ID` (pronunciation glossary for the synthesized speech, see below), `--speed 0.5-1.5`,
`--engine v|iv|iii` (default `v` when the look supports it), `--aspect 9:16` (default; also 16:9, 4:5, 5:4,
1:1, auto), `--resolution 1080p` (720p, 4k for Avatar III twins), `--motion "..."` (body and hand motion; engine v for
video avatars), `--title`, `--timeout 30m`, `--yes`, `--resume VIDEO_ID`.

What happens:

1. `status` and the look are read; the engine is checked against `supported_api_engines`; a landscape look asked for
   9:16 gets a warning (it will be cropped or letterboxed: record the twin vertically for Reels).
2. Duration is measured (audio) or estimated from the script (2.6 words/s) and the cost estimate is printed in the
   unit of the connection: premium credits on OAuth, USD on the API wallet. Rates are the published ones at release
   (Avatar V 48 credits/min on photo and video looks, or US$ 7.20/min for a twin on the API wallet; Avatar IV twin
   31 credits/min or US$ 4.83/min; photo 16 credits/min or US$ 2.31/min; Avatar III twin US$ 0.60/min). A 77 s
   Avatar V video on a photo look cost 63 credits in October 2026, in line with the table. HeyGen changes them and bills the real duration: the estimate exists
   so a person approves the spend, it is not the invoice.
3. Confirmation. Without a terminal the command stops and asks to re-run with `--yes`; **agents pass `--yes` only
   after the person who pays saw the estimate and approved it.** `--dry-run` never spends.
4. Audio is uploaded (`heygen asset create`), the video is requested with an idempotency key derived from the request
   and the input (a retry within 24 h does not bill twice), polled with backoff and downloaded to
   `<work>/source/avatar-<video_id>.mp4` with HeyGen's sidecar captions (`.srt`) and the script (`.txt`).
5. `<work>/avatar.json` records provider, video id, look, avatar type, engine, voice, input hash, billing mode,
   estimate, file SHA-256, size, duration, timestamps and `synthetic: true`. If the render outlives `--timeout`, the
   entry stays `rendering` and `heditor avatar <work> --resume <video_id>` downloads it later (exit code 4 meanwhile).

## The person's official voice

A synthetic video of a real person must speak with that person's own cloned voice, every time. HeyGen does not
guarantee it: `heygen avatar looks get` can return a stock voice as the `default_voice_id` of a photo look, even when
the avatar list shows the person's clone as its default. A request without `voice_id` would then put a stranger's
voice in the person's mouth.

- Set the official voice once in `~/.heditor/brand.json`: `"heygen": {"voice_id": "<id from heditor heygen voices>"}`
  (or `HEDITOR_HEYGEN_VOICE`). `heditor avatar` uses it whenever `--voice` is not passed and prints where the voice
  came from.
- Without a brand voice, `heditor avatar` uses the look's default voice only when it is one of the account's cloned
  voices; otherwise it stops and asks for `--voice`.
- When you call the HeyGen CLI directly (studio scenes, tests), always pass the official `voice_id` and never
  replace the voice with uploaded audio synthesized elsewhere.

## One motion prompt per sentence, with the person's voice selected (direct HeyGen CLI)

The person's configured voice is the one selected in the generation: `script` + `voice_id` per scene, with no
`voice_settings.engine_settings` override, so HeyGen uses the engine saved on that voice (the one the person trained
and listens to in HeyGen). Two shortcuts look tempting and are wrong for a person's own avatar:

- **Uploading audio synthesized elsewhere.** The video then has no voice selected in HeyGen, the glossary does not
  apply, and the audio may come from another engine (`voice speech create` refuses some saved engines and only offers
  `heygen_voice`, `starfish`, `elevenlabs`...), so it can sound unlike the voice the person knows. Use `--audio` only
  for the person's own recording.
- **Forcing an engine** (for example ElevenLabs v3 with delivery tags such as `[serious]`). Tags only work on that
  engine; on any other engine they are read aloud.

Recipe:

1. Split the spoken script into scenes of 3 to 10 s at sentence ends or commas, one gesture idea each.
2. Test the risky terms first with the same voice and the same saved engine: a 10–15 s `type: avatar` video on the
   cheapest engine (`avatar_iii` on a photo look cost 2 credits in October 2026) with the terms in context, then ASR.
3. One `type: studio` request: an `avatar_video` scene per slice with `script`, the official `voice_id`, the same look,
   `engine: {"type": "avatar_v", "reference_look_id": "<the person's digital twin>"}` and a `motion_prompt`
   ("[body part] + [action] + [emotion]", one gesture, under two clauses); `brand_glossary_id` at the top level applies
   to every scripted scene. `more_blinking` is rejected in studio videos. Validate against `--request-schema` and send
   with an idempotency key.
4. Direct a visible hand gesture in the first scenes: the opening seconds decide retention, and an avatar that only
   moves its head there reads as stiff. A short opening scene with one strong gesture works better than a long scene
   with a vague prompt.
5. Keep the eyes on the camera, alive like a conversation. Two failures give an avatar away: a gaze fixed on one point
   for the whole speech, and talking while looking to the side. Prompting glances ("glancing aside", "glancing at the
   hand") produced the second one: a scene spoke turned away for 8 s with the head at 30°. Give every scene a gesture +
   "keeping eye contact with the camera" + natural head motion ("nodding naturally", "small natural head
   movements"), and measure each scene before editing (eye-look blendshapes relative to the median and head yaw from
   MediaPipe Face Landmarker): a scene that stays off camera for 0.6 s or more is regenerated alone. `more_blinking`
   (outside `studio` only) made the avatar look down for most of a line, as if reading. A scene can also start with
   0.2–0.6 s of a head dip and warped glasses in the silent lead-in: check the first second of each scene and trim it.
6. Check the result: ASR word by word against the approved script, hands, teeth, eyes, gaze and mouth on enlarged frames.
   Every scene start resets the pose: plan a framing change or transition there. A defective scene is regenerated
   alone (one scene of the same recipe), never the whole video.

## Writing the script for the voice (pronunciation and natural speech)

The synthesized voice reads exactly what is written, letter by letter and mark by mark. A foreign term read with the
wrong phonetics, a number read as digits or a script cut into three-word sentences is what makes a clone sound like a
robot. Prepare the speech before any credit is spent.

**Two texts, one meaning.**

- `roteiro.txt` is the approved script, written normally. It is what the person approves, and it is the spelling of
  the captions (`words-reviewed.json`).
- `roteiro-fala.txt` is the spoken version sent to `--script`. It has the same words and the same meaning, prepared
  for the voice: numbers written as they are said, abbreviations expanded, pauses marked and, only where no glossary
  covers a term, respellings. Show the diff between the two; it must change pronunciation only, never content.

**1. Mark every risky word** before generating:

- foreign terms inside the script's language (tool names, brands, technical jargon in English inside a Portuguese
  script);
- acronyms: decide whether each one is spelled letter by letter or read as a word, the way the person says it;
- names of products, people and places;
- numbers, money, dates, times, percentages, versions, multipliers and ratios (`R$ 197`, `2026`, `30%`, `v2.1`,
  `12x`, `9:16`);
- handles, URLs and e-mail addresses;
- symbols and abbreviations (`/`, `&`, `+`, `→`, `#`, `@`, `etc.`, `ex.`, chat shorthand), emojis, markdown,
  parentheses and quotes;
- homographs whose pronunciation depends on the meaning.

**2. Use a pronunciation glossary for recurring terms.** A HeyGen brand glossary maps a written term to the respelling
handed to the synthesizer. It changes the audio only: HeyGen's captions keep the written term, so the approved
spelling survives. It applies to `--script`/`--text`, never to an `--audio` file.

```bash
heditor heygen glossaries                         # existing glossaries and their terms
heygen brand glossaries create --request-schema   # fields: name, terms[{term, pronunciation, pronunciation_language}]
heygen brand glossaries update <id> -d -          # terms is a FULL REPLACE: send every existing term + the new ones
heditor avatar <work> --look ID --script roteiro-fala.txt --glossary <id> --dry-run
```

- `update` replaces the whole `terms` list: read the glossary (`heygen brand glossaries get <id>`), keep every entry
  with its `pronunciation_language`, add the new ones and send the full list, or the old terms are lost.

- Write each respelling in the phonetics of the voice's language, the way the person really says the term: take it
  from their own recordings or ask them. Never assume the original-language pronunciation if they say it the local
  way.
- Scope a respelling to one language (`pronunciation_language` with scope `specific` and a code such as `pt`) when it
  only makes sense in that language.
- Keep one glossary per account as the single source of truth and record its id in DESIGN.md.

**3. Write in the spoken script what a glossary cannot cover.** Numbers as said ("cento e noventa e sete reais",
"dois mil e vinte e seis", "doze vezes", "nove por dezesseis", "versão dois ponto um", "trinta por cento"); handles
and URLs as said; abbreviations expanded; emojis, symbols, markdown, parentheses and quotes removed. A one-off term
can be respelled inline; then HeyGen's `.srt` and the ASR show the respelling, and `words-reviewed.json` gets the
approved spelling back (timings untouched).

**4. Write for continuous speech.** The voice takes its intonation from the punctuation.

- One idea per sentence, about 8 to 20 words, linked with ordinary connectives ("e", "mas", "porque", "então").
  Strings of very short sentences read staccato and robotic; a 40-word sentence with no comma reads breathless.
- Commas where the person would breathe, a period where the voice should fall, a question mark only on real
  questions (it raises the intonation).
- Avoid ellipses (unpredictable long pauses), dashes, colons and semicolons in the middle of speech, parentheses and
  chains of exclamation marks.
- One paragraph per thought, never one line per sentence: line and paragraph breaks can turn into long pauses.
- Pauses: `<break time="0.4s"/>`, in seconds (milliseconds are rejected by HeyGen and by heditor), 0.2 to 0.6 s,
  only at real beats such as after the hook or before a reveal. Never stack them.
- Spoken register: first person, the contractions and fillers the person really uses (in Brazilian Portuguese,
  "pra", "tá", "né", in moderation), no written-only vocabulary.
- Keep the voice at its natural pace. `--speed` (0.5 to 1.5) only after listening, and small steps (0.95 to 1.05);
  beyond that it sounds synthetic.

**5. Test the risky terms before the video.** Generate a short audio sample with the cloned voice instead of a whole
video: `heygen voice speech create` (read `--request-schema`; it takes the respelling inline, has no glossary field
and uses HeyGen's speech quota, so compare the balance before and after the first test). Listen to it, then add the
respellings that worked to the glossary.

**6. Check the generated video word by word.** Transcribe it (`heditor words` after `heditor new`, or `heditor
transcribe`) and compare with the approved script. Every word the ASR gets wrong is a candidate mispronunciation:
listen to that passage. Fix it in the glossary or the spoken script and regenerate that line (a shorter scene)
instead of hiding it under captions or music. Listen to the whole take once for flow: no robotic rhythm, no pause in
the middle of a phrase, no word stressed on the wrong syllable.

`heditor avatar` records `glossary_id` and `speed` in `avatar.json` and saves the spoken script next to the video
(`source/avatar-<video_id>.txt`).

## Editing an avatar video

- The avatar file is a source like any recording: `heditor new`, `prepare` (one block covering the speech, crop if
  needed), `words` (HeyGen's `.srt` is only a reference; `words-reviewed.json` stays the caption source), `gaps`,
  DESIGN.md, build, produce, QA, render.
- Choose layouts that are kind to synthetic faces: cut-outs and screens in front of the speaker (`reacao`, `camadas`,
  `manchete`), b-roll and set pieces on the strongest lines. Inspect teeth, eyes, hands and lip sync on enlarged
  frames of the contact sheet; regenerate the line (shorter script, other look) instead of hiding a defect.
- Pacing comes from the script: there are no retakes to trim, so `gaps` usually passes. Write for speech with the
  hook in the first words and follow "Writing the script for the voice" above.
- **Scene seams (studio videos, one scene per sentence).** Every scene starts from the look's rest pose, so each seam
  is a pose jump. List the seams (source time of the first frame of each new scene, measured on the frame difference)
  in the work and pass them to the prepare: `prepare_cut(..., seams=[...])` moves each pause trim so its cut lands
  exactly on the seam inside the pause, removing the same time. Without it, a seam that falls in a kept edge of a
  pause becomes two jumps a few frames apart (trim cut, then pose reset); hiding the speaker for those frames reads as
  a vanish/flicker and was rejected. Cover the single jump with a framing change on the cut.
- **Joined renders.** When the source is spliced from several renders (scenes regenerated alone), check the audio at
  every splice at 1 ms resolution: cutting a frame late can keep the first milliseconds of the next word (a click of
  -25 dB in a -65 dB pause). Mute the burst in the source before the prepare. Also look at the first second of every
  regenerated scene: a scene can open with 0.2-0.6 s of head dip, closed eyes and warped glasses in its silent
  lead-in; start the splice after it.
- **Cut-outs.** The speaker matte of a synthetic plate can keep a faint alpha over the whole background (the office
  shelf showing through as a ghost over a graphic wall). `person_matte` removes it with `floor` (default 0.09); check
  `background_haze` in `qa/matte-stats.json` and the matte sheet before building layers on top.

## Truth, consent and disclosure

- Only the person's own avatar (or one they have documented consent to use). HeyGen verifies consent when a digital
  twin is created; heditor does not create avatars or clone voices.
- The person approves every script. The avatar never says something the person did not approve: no invented numbers,
  testimonials, promises or claims (the same truth rules as every edit).
- Disclose AI use where a platform or a law asks for it. Meta, for example, may label ads made with third-party AI
  tools ("AI info") and requires disclosure for ads about social issues, elections or politics.
- Keep the account protected (2FA on HeyGen) and the credential out of repositories and chats: a voice and face clone
  is a fraud vector if it leaks.
