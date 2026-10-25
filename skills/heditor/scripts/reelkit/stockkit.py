#!/usr/bin/env python3
"""stockkit: free stock video (B-roll) for heditor from Mixkit, with no account and no API key.

Mixkit publishes its free clips on public listing pages and serves the files from its official CDN
(assets.mixkit.co) under the Mixkit Stock Video Free License (commercial use, social posts, online ads and YouTube
allowed; attribution not required). Search terms are English. Every download records its provenance in
<work>/stock.json and the licence is confirmed on the clip page before the file is fetched.

Mixkit's User Terms forbid scripts that mass-download or scrape the library: this tool fetches one listing page per
search (cached 24 h) and one clip per `get`, for the clips an edit actually uses. Never loop it to build a library.

CLI (through `heditor`):
  heditor stock search "<query>" [--orientation portrait|landscape|square|any] [--limit N] [--page N] [--json]
  heditor stock get <work|dir> <#n|mixkit:video:ID|clip-page-url> [--quality 1080|4k|best|720] [--as name]
"""
import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Mixkit serves its pages to browsers; the CDN files are public.
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/130.0 Safari/537.36")
CACHE_TTL_S = 24 * 3600
LISTING = "https://mixkit.co/free-stock-video/discover/{slug}/"
FILE_URL = "https://assets.mixkit.co/videos/{id}/{id}-{size}.mp4"
SIZES = (2160, 1080, 720, 360)  # not every clip has every size: tried in order at download
LICENSE = "Mixkit Stock Video Free License"
LICENSE_URL = "https://mixkit.co/license/#videoFree"
CREDIT = "Videos from Mixkit (https://mixkit.co), Mixkit Stock Video Free License"


class StockError(RuntimeError):
    pass


def heditor_home():
    return Path(os.environ.get("HEDITOR_HOME", "~/.heditor")).expanduser()


# ---------------------------------------------------------------- http and cache

def _http(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), r.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() if exc.fp else b"", url


def _cached(key_parts, fetch, ttl=CACHE_TTL_S):
    digest = hashlib.sha256(json.dumps(key_parts, sort_keys=True).encode()).hexdigest()[:24]
    path = heditor_home() / "cache/stock" / f"{digest}.json"
    if path.exists() and time.time() - path.stat().st_mtime < ttl:
        return json.loads(path.read_text())
    data = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


# ---------------------------------------------------------------- parsing

def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def orientation(w, h):
    if not w or not h:
        return "any"
    r = w / h
    return "square" if 0.9 <= r <= 1.1 else ("landscape" if r > 1 else "portrait")


def _files(vid):
    return [{"url": FILE_URL.format(id=vid, size=s), "label": str(s)} for s in SIZES]


def _item(vid, title="", description="", page_url="", aspect=(16, 9)):
    return {"ref": f"mixkit:video:{vid}", "id": str(vid), "title": title, "description": description,
            "orientation": orientation(*aspect), "aspect": list(aspect), "page_url": page_url,
            "preview": FILE_URL.format(id=vid, size=360), "files": _files(vid), "license": LICENSE,
            "license_url": LICENSE_URL}


def parse_cards(page_html):
    """Video cards of a Mixkit listing page -> items. The thumbnail size gives the orientation."""
    items = []
    for card in re.split(r'<div class="item-grid-card(?: |")', page_html)[1:]:
        m_id = re.search(r'video-player-item-id-value="(\d+)"', card)
        m_link = re.search(r'href="(/free-stock-video/[a-z0-9-]+-\d+/)"', card)
        if not (m_id and m_link):
            continue
        m_title = re.search(r'overlay-video-title">\s*([^<]+?)\s*</span>', card)
        m_desc = re.search(r'overlay-video-description">\s*([^<]+?)\s*</span>', card)
        m_dim = re.search(r'class="item-grid-video-player__thumb"[^>]*width="(\d+)" height="(\d+)"', card)
        aspect = (int(m_dim.group(1)), int(m_dim.group(2))) if m_dim else (16, 9)
        items.append(_item(m_id.group(1), html.unescape(m_title.group(1)) if m_title else "",
                           html.unescape(m_desc.group(1)) if m_desc else "", "https://mixkit.co" + m_link.group(1),
                           aspect))
    return items


def _title_from_url(url):
    m = re.search(r"/free-stock-video/([a-z0-9-]+?)-\d+/?$", url or "")
    return m.group(1).replace("-", " ").capitalize() if m else ""


def parse_ref(ref):
    """'mixkit:video:123' or a Mixkit clip page URL -> (id, page_url); None if not recognised."""
    ref = ref.strip()
    m = re.fullmatch(r"mixkit:video:(\d+)", ref)
    if m:
        return m.group(1), ""
    m = re.search(r"mixkit\.co/free-stock-video/[a-z0-9-]+-(\d+)/?", ref)
    if m:
        return m.group(1), ref
    return None


# ---------------------------------------------------------------- search

def search(query, orient="any", page=1, limit=12):
    """(items, notes). Mixkit pages hold 24 clips; orientation is filtered on this page only."""
    slug = slugify(query)
    if not slug:
        raise StockError("empty query")
    first = LISTING.format(slug=slug)

    def fetch():
        code, body, final = _http(first)
        if code != 200:
            raise StockError(f"Mixkit HTTP {code} for {first}")
        text = body.decode("utf-8", "replace")
        if page > 1:
            # Paginate on the canonical URL: some discover pages redirect to a tag page, and ?page=N on the
            # redirecting URL silently returns page 1 again.
            code, body, _ = _http(final.split("?")[0] + f"?page={page}")
            text = body.decode("utf-8", "replace") if code == 200 else ""
        return parse_cards(text)

    found = _cached(["mixkit", first, page], fetch)
    notes = []
    if not found:
        notes.append("Mixkit found nothing. It searches in English: try other words ('server room', "
                     "'typing on laptop', 'city at night') or a single noun.")
    kept = [i for i in found if orient == "any" or i["orientation"] == orient]
    if found and not kept:
        notes.append(f"{len(found)} clip(s) on this page, none {orient}: try --page {page + 1}, other words, or "
                     "--orientation any and crop in the composition")
    return kept[:limit], notes


def _last_search_path():
    return heditor_home() / "cache/stock/last-search.json"


def save_last_search(query, items):
    path = _last_search_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"query": query, "time": time.time(), "items": items}))


def resolve(ref):
    """'#3' / '3' (last search), 'mixkit:video:ID' or a clip page URL -> item."""
    last = json.loads(_last_search_path().read_text()) if _last_search_path().exists() else {"items": []}
    m = re.fullmatch(r"#?(\d{1,3})", ref.strip())
    if m:
        n = int(m.group(1))
        if not 1 <= n <= len(last["items"]):
            raise StockError(f"no result #{n} in the last search ({len(last['items'])} results); "
                             "run `heditor stock search` first")
        return last["items"][n - 1]
    parsed = parse_ref(ref)
    if not parsed:
        raise StockError(f"not a Mixkit reference: {ref!r} (use #N from the last search, mixkit:video:ID or the "
                         "clip page URL https://mixkit.co/free-stock-video/...-ID/)")
    vid, page_url = parsed
    for it in last["items"]:
        if it["id"] == vid:
            return it
    if not page_url:
        raise StockError(f"mixkit:video:{vid} is not in the last search: pass the clip page URL instead")
    return _item(vid, _title_from_url(page_url), page_url=page_url)


# ---------------------------------------------------------------- download

def size_order(quality="1080"):
    return {"best": SIZES, "4k": SIZES, "1080": (1080, 2160, 720, 360), "720": (720, 1080, 360, 2160)}[quality]


def check_license(page_url):
    code, body, _ = _http(page_url)
    if code != 200:
        raise StockError(f"could not open the clip page to confirm the licence (HTTP {code}): {page_url}")
    if LICENSE not in body.decode("utf-8", "replace"):
        raise StockError(f"the clip page does not show the {LICENSE}: {page_url}; pick another clip")


def _ffprobe(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height:format=duration", "-of", "json", str(path)],
                             capture_output=True, text=True, timeout=60, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    data = json.loads(out)
    st = (data.get("streams") or [{}])[0]
    info = {"width": st.get("width"), "height": st.get("height")}
    dur = (data.get("format") or {}).get("duration")
    if dur:
        info["duration"] = round(float(dur), 2)
    return info


def _download(url, dest):
    tmp = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(req, timeout=300) as r, tmp.open("wb") as f:
        ctype = r.headers.get("Content-Type", "")
        while chunk := r.read(1 << 20):
            f.write(chunk)
    if tmp.stat().st_size < 1024 or "video" not in ctype:
        tmp.unlink(missing_ok=True)
        raise StockError(f"download returned no video ({ctype or 'empty'}): {url}")
    os.replace(tmp, dest)


def get(target, ref, quality="1080", name=None):
    """Download a clip into <work>/composition/assets/stock/ (or any folder) and record it in <target>/stock.json."""
    item = resolve(ref)
    target = Path(target).expanduser().resolve()
    comp = target / "composition"
    out_dir = comp / "assets/stock" if comp.is_dir() else target
    out_dir.mkdir(parents=True, exist_ok=True)
    check_license(item["page_url"])
    dest = out_dir / f"{slugify(name) if name else 'mixkit-video-' + item['id']}.mp4"
    url, last_err = None, None
    for size in size_order(quality):
        candidate = FILE_URL.format(id=item["id"], size=size)
        try:
            _download(candidate, dest)
            url = candidate
            break
        except (urllib.error.HTTPError, StockError) as exc:
            last_err = exc
    if not url:
        raise StockError(f"could not download {item['ref']}: {last_err}")
    probe = _ffprobe(dest)
    rel = dest.relative_to(comp) if comp.is_dir() else Path(dest.name)
    record = {
        "ref": item["ref"], "title": item["title"], "source": "Mixkit", "page_url": item["page_url"],
        "download_url": url, "license": LICENSE, "license_url": LICENSE_URL, "file": str(rel),
        "bytes": dest.stat().st_size, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        "width": probe.get("width"), "height": probe.get("height"), "duration": probe.get("duration"),
        "downloaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    prov_path = target / "stock.json"
    prov = json.loads(prov_path.read_text()) if prov_path.exists() else []
    prov = [p for p in prov if p.get("file") != record["file"]] + [record]
    prov_path.write_text(json.dumps(prov, indent=2, ensure_ascii=False) + "\n")
    return record, prov_path


def design_line(rec):
    size = f"{rec['width']}x{rec['height']}" + (f", {rec['duration']} s" if rec.get("duration") else "")
    return (f"- `{rec['file']}`: Mixkit video \"{rec['title']}\" ({size}), {rec['page_url']}, "
            f"{rec['license']} ({rec['license_url']})")


# ---------------------------------------------------------------- CLI

def cmd_search(a):
    items, notes = search(a.query, a.orientation, a.page, a.limit)
    save_last_search(a.query, items)
    if a.json:
        print(json.dumps({"query": a.query, "items": items, "notes": notes}, indent=2, ensure_ascii=False))
        return 0 if items else 1
    print(f"{CREDIT}\n\n{len(items)} clip(s) for {a.query!r}" + (":\n" if items else ""))
    for n, it in enumerate(items, 1):
        print(f"#{n:<3} {it['ref']:<20} {it['orientation']:<9} {it['title'][:70]}\n      {it['page_url']}")
    if notes:
        print()
    for note in notes:
        print(f"note: {note}")
    if items:
        print("\nPreview: open the page URL. Download: heditor stock get <work> #<n>   (provenance -> <work>/stock.json)")
    return 0 if items else 1


def cmd_get(a):
    rec, prov_path = get(a.target, a.ref, a.quality, a.name)
    print(f"downloaded {rec['file']} ({rec['width']}x{rec['height']}"
          + (f", {rec['duration']} s" if rec.get("duration") else "") + f", {rec['bytes'] / 1e6:.1f} MB)")
    print(f"provenance -> {prov_path}")
    print("DESIGN.md (Licences / provenance):\n" + design_line(rec))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    sub, rest = (argv[0], argv[1:]) if argv else ("help", [])
    try:
        if sub == "search":
            ap = argparse.ArgumentParser(prog="heditor stock search")
            ap.add_argument("query", help="English words, e.g. \"server room\"")
            ap.add_argument("--orientation", default="any", choices=("any", "portrait", "landscape", "square"))
            ap.add_argument("--limit", type=int, default=12)
            ap.add_argument("--page", type=int, default=1)
            ap.add_argument("--json", action="store_true")
            return cmd_search(ap.parse_args(rest))
        if sub == "get":
            ap = argparse.ArgumentParser(prog="heditor stock get")
            ap.add_argument("target", help="work dir (file goes to composition/assets/stock/) or any folder")
            ap.add_argument("ref", help="#N from the last search, mixkit:video:ID or the clip page URL")
            ap.add_argument("--quality", default="1080", choices=("1080", "4k", "best", "720"))
            ap.add_argument("--as", dest="name", help="file name without extension")
            return cmd_get(ap.parse_args(rest))
    except StockError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"error: Mixkit unreachable ({exc})", file=sys.stderr)
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
