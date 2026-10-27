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
heditor avatar cortes/c01 --look <id> --script roteiro.txt --dry-run   # plan, estimate and request; spends nothing
heditor avatar cortes/c01 --look <id> --script roteiro.txt              # asks for confirmation, then renders
heditor new cortes/c01 cortes/c01/source/avatar-<video_id>.mp4          # then the normal workflow
```

Inputs (exactly one): `--script FILE`, `--text "..."` (the look's default voice, or `--voice ID`) or `--audio FILE`
(mp3/wav lip-synced as is; for example the person's own recording, so only the picture is synthetic).

Options: `--engine v|iv|iii` (default `v` when the look supports it), `--aspect 9:16` (default; also 16:9, 4:5, 5:4,
1:1, auto), `--resolution 1080p` (720p, 4k for Avatar III twins), `--motion "..."` (body and hand motion; engine v for
video avatars), `--title`, `--timeout 30m`, `--yes`, `--resume VIDEO_ID`.

What happens:

1. `status` and the look are read; the engine is checked against `supported_api_engines`; a landscape look asked for
   9:16 gets a warning (it will be cropped or letterboxed: record the twin vertically for Reels).
2. Duration is measured (audio) or estimated from the script (2.6 words/s) and the cost estimate is printed in the
   unit of the connection: premium credits on OAuth, USD on the API wallet. Rates are the published ones at release
   (Avatar V 48 credits/min or US$ 7.20/min; Avatar IV twin 31 credits/min or US$ 4.83/min; photo 16 credits/min or
   US$ 2.31/min; Avatar III twin US$ 0.60/min). HeyGen changes them and bills the real duration: the estimate exists
   so a person approves the spend, it is not the invoice.
3. Confirmation. Without a terminal the command stops and asks to re-run with `--yes`; **agents pass `--yes` only
   after the person who pays saw the estimate and approved it.** `--dry-run` never spends.
4. Audio is uploaded (`heygen asset create`), the video is requested with an idempotency key derived from the request
   and the input (a retry within 24 h does not bill twice), polled with backoff and downloaded to
   `<work>/source/avatar-<video_id>.mp4` with HeyGen's sidecar captions (`.srt`) and the script (`.txt`).
5. `<work>/avatar.json` records provider, video id, look, avatar type, engine, voice, input hash, billing mode,
   estimate, file SHA-256, size, duration, timestamps and `synthetic: true`. If the render outlives `--timeout`, the
   entry stays `rendering` and `heditor avatar <work> --resume <video_id>` downloads it later (exit code 4 meanwhile).

## Editing an avatar video

- The avatar file is a source like any recording: `heditor new`, `prepare` (one block covering the speech, crop if
  needed), `words` (HeyGen's `.srt` is only a reference; `words-reviewed.json` stays the caption source), `gaps`,
  DESIGN.md, build, produce, QA, render.
- Choose layouts that are kind to synthetic faces: cut-outs and screens in front of the speaker (`reacao`, `camadas`,
  `manchete`), b-roll and set pieces on the strongest lines. Inspect teeth, eyes, hands and lip sync on enlarged
  frames of the contact sheet; regenerate the line (shorter script, other look) instead of hiding a defect.
- Pacing comes from the script: there are no retakes to trim, so `gaps` usually passes; long sentences read flat.
  Write for speech, short clauses, the hook in the first words.

## Truth, consent and disclosure

- Only the person's own avatar (or one they have documented consent to use). HeyGen verifies consent when a digital
  twin is created; heditor does not create avatars or clone voices.
- The person approves every script. The avatar never says something the person did not approve: no invented numbers,
  testimonials, promises or claims (the same truth rules as every edit).
- Disclose AI use where a platform or a law asks for it. Meta, for example, may label ads made with third-party AI
  tools ("AI info") and requires disclosure for ads about social issues, elections or politics.
- Keep the account protected (2FA on HeyGen) and the credential out of repositories and chats: a voice and face clone
  is a fraud vector if it leaks.
