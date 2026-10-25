"""Unit tests for stockkit (Mixkit stock video): parsing, references, cache, provenance. No network."""
import json

import pytest

import stockkit as sk

CARD = """
<div class="item-grid-card" data-algolia-analytics-object-id="video-{id}">
 <div class="item-grid-video-player" data-item-grid--video-player-item-id-value="{id}"
  data-item-grid--video-player-item-type-value="Video">
  <img src="https://assets.mixkit.co/videos/{id}/{id}-thumb-360-0.jpg" class="item-grid-video-player__thumb"
   alt="x" width="{w}" height="{h}" loading="lazy">
  <span class="item-grid-video-player__overlay-video-title"> {title} </span>
  <span class="item-grid-video-player__overlay-video-description"> A desc &amp; more. </span>
  <a href="/free-stock-video/{slug}-{id}/" class="item-grid-video-player__overlay-link">{title}</a>
 </div>
</div>
"""


def page(*cards):
    return "<html>" + "".join(CARD.format(**c) for c in cards) + "</html>"


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDITOR_HOME", str(tmp_path / "home"))
    return tmp_path


def test_slugify_strips_accents_and_symbols():
    assert sk.slugify("Sala de Servidores!") == "sala-de-servidores"
    assert sk.slugify("  typing   on laptop ") == "typing-on-laptop"
    assert sk.slugify("ção") == "cao"


def test_orientation():
    assert sk.orientation(460, 818) == "portrait"
    assert sk.orientation(460, 259) == "landscape"
    assert sk.orientation(500, 480) == "square"
    assert sk.orientation(0, 0) == "any"


def test_parse_cards():
    items = sk.parse_cards(page({"id": 41654, "w": 460, "h": 818, "title": "Code on a screen", "slug": "code"},
                                {"id": 914, "w": 460, "h": 259, "title": "Open office", "slug": "open-office"}))
    assert [i["ref"] for i in items] == ["mixkit:video:41654", "mixkit:video:914"]
    first = items[0]
    assert first["orientation"] == "portrait"
    assert first["title"] == "Code on a screen"
    assert first["description"] == "A desc & more."
    assert first["page_url"] == "https://mixkit.co/free-stock-video/code-41654/"
    assert first["files"][0]["url"] == "https://assets.mixkit.co/videos/41654/41654-2160.mp4"
    assert first["license"] == sk.LICENSE
    assert items[1]["orientation"] == "landscape"


def test_parse_cards_ignores_non_video_blocks():
    assert sk.parse_cards('<div class="item-grid-card__meta">nothing</div>') == []


def test_parse_ref():
    assert sk.parse_ref("mixkit:video:918") == ("918", "")
    url = "https://mixkit.co/free-stock-video/busy-office-space-918/"
    assert sk.parse_ref(url) == ("918", url)
    assert sk.parse_ref("pexels:video:1") is None
    assert sk.parse_ref("hello") is None


def test_size_order():
    assert sk.size_order("1080")[0] == 1080
    assert sk.size_order("4k")[0] == 2160
    assert sk.size_order("720")[0] == 720


def test_search_filters_orientation_and_caches(monkeypatch):
    html_page = page({"id": 1, "w": 460, "h": 818, "title": "Vertical", "slug": "v"},
                     {"id": 2, "w": 460, "h": 259, "title": "Wide", "slug": "w"})
    calls = []

    def fake_http(url, timeout=30):
        calls.append(url)
        return 200, html_page.encode(), url

    monkeypatch.setattr(sk, "_http", fake_http)
    items, notes = sk.search("Server Room", "portrait")
    assert [i["id"] for i in items] == ["1"] and not notes
    assert calls == ["https://mixkit.co/free-stock-video/discover/server-room/"]
    sk.search("server room", "any")  # same listing page: served from the 24 h cache
    assert len(calls) == 1
    items, notes = sk.search("server room", "square")
    assert items == [] and "none square" in notes[0]


def test_search_empty_explains_english(monkeypatch):
    monkeypatch.setattr(sk, "_http", lambda url, timeout=30: (200, b"<html></html>", url))
    items, notes = sk.search("sala de servidores")
    assert items == [] and "English" in notes[0]


def test_search_paginates_on_canonical_url(monkeypatch):
    calls = []

    def fake_http(url, timeout=30):
        calls.append(url)
        return 200, b"<html></html>", "https://mixkit.co/free-stock-video/programming/"

    monkeypatch.setattr(sk, "_http", fake_http)
    sk.search("programming", page=2)
    assert calls[-1] == "https://mixkit.co/free-stock-video/programming/?page=2"


def test_resolve_from_last_search_and_url():
    items = sk.parse_cards(page({"id": 7, "w": 460, "h": 818, "title": "Seven", "slug": "seven"}))
    sk.save_last_search("q", items)
    assert sk.resolve("#1")["id"] == "7"
    assert sk.resolve("1")["id"] == "7"
    assert sk.resolve("mixkit:video:7")["title"] == "Seven"
    url = "https://mixkit.co/free-stock-video/busy-office-space-918/"
    it = sk.resolve(url)
    assert it["id"] == "918" and it["title"] == "Busy office space" and it["page_url"] == url
    with pytest.raises(sk.StockError):
        sk.resolve("#5")
    with pytest.raises(sk.StockError):
        sk.resolve("mixkit:video:999")  # not in the last search and no page URL


def test_get_writes_file_and_provenance(monkeypatch, tmp_path):
    work = tmp_path / "work"
    (work / "composition").mkdir(parents=True)
    sk.save_last_search("q", sk.parse_cards(page({"id": 7, "w": 460, "h": 818, "title": "Seven", "slug": "s"})))
    monkeypatch.setattr(sk, "check_license", lambda url: None)
    tried = []

    def fake_download(url, dest):
        tried.append(url)
        if "-1080." in url:
            raise sk.StockError("no such size")
        dest.write_bytes(b"\0" * 4096)

    monkeypatch.setattr(sk, "_download", fake_download)
    monkeypatch.setattr(sk, "_ffprobe", lambda p: {"width": 1080, "height": 1920, "duration": 7.1})
    rec, prov_path = sk.get(work, "#1")
    assert tried[0].endswith("7-1080.mp4") and tried[1].endswith("7-2160.mp4")
    assert rec["file"] == "assets/stock/mixkit-video-7.mp4"
    assert (work / "composition/assets/stock/mixkit-video-7.mp4").exists()
    prov = json.loads(prov_path.read_text())
    assert prov_path == work / "stock.json" and len(prov) == 1
    assert prov[0]["license"] == sk.LICENSE and prov[0]["sha256"] and prov[0]["download_url"] == tried[1]
    sk.get(work, "#1")  # same file again: provenance entry replaced, not duplicated
    assert len(json.loads(prov_path.read_text())) == 1
    assert "assets/stock/mixkit-video-7.mp4" in sk.design_line(rec)


def test_get_refuses_without_licence(monkeypatch, tmp_path):
    sk.save_last_search("q", sk.parse_cards(page({"id": 7, "w": 460, "h": 818, "title": "Seven", "slug": "s"})))
    monkeypatch.setattr(sk, "_http", lambda url, timeout=30: (200, b"<html>Premium item</html>", url))
    with pytest.raises(sk.StockError, match="does not show"):
        sk.get(tmp_path, "#1")
