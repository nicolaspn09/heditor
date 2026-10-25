# Stock video (B-roll) from Mixkit

`heditor stock` searches Mixkit's free stock videos and downloads a clip into the work dir with its provenance. No
account, no API key, nothing to configure: it works right after setup.

## Why Mixkit (and not the others)

| Source | Free licence | Why it is (not) in heditor |
|---|---|---|
| **Mixkit** (mixkit.co) | Mixkit Stock Video Free License: commercial use, social posts, online ads, YouTube; attribution not required | Public listing pages + official CDN, no key. Same provider as the music and SFX catalog. **Built in.** |
| Pexels, Pixabay | free licences, no attribution required | Good libraries, but the API needs each user's own key. Left out on purpose so nobody has to create accounts; a user can still download from their sites by hand and record provenance the same way. |
| Unsplash | free licence | Photos only; the API demands hotlinking, a download ping and attribution. |
| Adobe Stock | free collection needs an Adobe account | API restricted to Stock for Enterprise / approved affiliates since Nov 2024. |
| Videezy | free clips require visible attribution; some are editorial only | No API; free and paid Pro clips are mixed. |

## Commands

```bash
heditor stock search "server room"                          # 12 clips from the first page, with orientation
heditor stock search "programming" --orientation portrait   # only vertical clips (filtered on that page)
heditor stock search "city at night" --page 2 --limit 20
heditor stock get <work> '#2'                               # number from the last search
heditor stock get <work> https://mixkit.co/free-stock-video/busy-office-space-918/ --as escritorio
heditor stock get <work> mixkit:video:41658 --quality 4k    # 1080 (default), 4k/best, 720
```

- **Search in English.** Mixkit pages are English only: "server room", "typing on laptop", "data center", "city at
  night", "abstract technology". A Portuguese query returns nothing and the CLI says so.
- **Orientation** comes from the listing thumbnail and is filtered on the page fetched (24 clips per page). For 9:16 try
  `--orientation portrait`, then `--page 2`; a landscape clip also works when cropped with `object-fit: cover` (check the
  subject stays inside the crop).
- **Quality**: the default takes the 1080 file and falls back to 2160, 720, 360 (not every clip has every size).
  `--quality 4k` for zoomed punch-ins on the B-roll.
- Listings are cached 24 h in `~/.heditor/cache/stock/`; the last search is kept so `#N` works in `stock get`.

## What `stock get` guarantees

1. Opens the clip page and refuses the download unless it shows **Mixkit Stock Video Free License**.
2. Downloads from `assets.mixkit.co` into `<work>/composition/assets/stock/` (or into any folder given instead of a work
   dir) and checks the response is a video.
3. Probes the real size and duration with ffprobe.
4. Appends a record to `<work>/stock.json`: ref, title, page URL, download URL, licence and URL, file, bytes, SHA-256,
   width, height, duration, download time. Re-downloading the same file replaces its record.
5. Prints the line to paste in DESIGN.md (Licences / provenance). Do it: the provenance is part of the delivery.

## Using a clip in the composition

- Hand-written page: `<video id="broll-1" class="clip" data-start="12.4" data-duration="2.6" data-track-index="5"
  src="assets/stock/mixkit-video-41658.mp4" muted playsinline></video>` (every media element needs a unique `id`, or
  HyperFrames lint fails). Use `data-media-start` to pick the best seconds of the clip.
- `rk.page(..., videos=[{"id": "broll-1", "src": "stock/mixkit-video-41658.mp4", "start": 12.4, "duration": 2.6,
  "track": 5}])` (the kit prefixes `assets/`).
- Always `muted`: the voice and the mix stay in control. Stock audio never reaches the master.
- Grade the clip toward the edit's palette with CSS (`filter`, overlays, blend modes); never re-colour the speaker's own
  footage (that stays untouched).

## Choosing B-roll that serves the speech

- One clip per idea, on the word that names it, 1.5–3 s; never wallpaper. B-roll illustrates; the speaker and the
  graphics still carry the argument.
- Prefer clips without recognisable faces in paid ads: a stranger on screen next to a claim reads as a testimonial
  (heditor's rule: no invented testimonials).
- No visible third-party logos, brands or readable product UIs (heditor's truth and licence rules still apply).
- Never label a stock clip as the speaker's own work, client, office or result.

## Mixkit User Terms that bind this tool (https://mixkit.co/terms/)

- **No mass downloading.** Scripts or bots that scrape or download the library are forbidden. `heditor stock` fetches
  one listing page per search (cached 24 h) and one clip per `get`, only the clips an edit uses. Never loop it over
  queries or pages to build a local library.
- **No redistribution as stock.** Clips may not be resold, sublicensed or made available on a stock basis: they live in
  the work dir and reach people only inside the finished video.
- Use follows the Mixkit License and Envato's Acceptable Use Policy; Mixkit can revoke the licence for a breach.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Mixkit found nothing` | English words, fewer of them, or a single noun (`laptop`, `server`, `code`). |
| `none portrait on this page` | `--page 2`, other words, or a landscape clip cropped with `object-fit: cover`. |
| `does not show the Mixkit Stock Video Free License` | That item is not under the free licence: pick another clip. |
| `is not in the last search` | Pass the clip page URL instead of `mixkit:video:ID`. |
| HTTP 403/5xx from mixkit.co | Temporary block or outage: wait and retry; cached searches keep working for 24 h. |
