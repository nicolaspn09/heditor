"""Tests for heygenkit (optional HeyGen connection and AI avatar videos). No network: a fake `heygen` CLI."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import heygenkit  # noqa: E402

SECRET = "sk_test_never_printed_123"

FAKE_CLI = r'''#!/usr/bin/env python3
import json, os, shutil, sys
args = sys.argv[1:]
stdin = sys.stdin.read() if "-" in args else ""
with open(os.environ["FAKE_LOG"], "a") as fh:
    fh.write(json.dumps({"args": args, "stdin": stdin}) + "\n")
mode = os.environ.get("FAKE_MODE", "oauth")
flag = os.environ.get("FAKE_LOGGED_FILE", "")
if flag and os.path.exists(flag):
    mode = "oauth"
def out(obj, code=0):
    print(json.dumps(obj)); sys.exit(code)
def err(code, message, rc):
    sys.stderr.write(json.dumps({"error": {"code": code, "message": message, "hint": "run heygen auth login"}}))
    sys.exit(rc)
if args == ["--version"]:
    print("heygen version v0.11.0"); sys.exit(0)
if args[:2] == ["auth", "status"]:
    if mode == "none":
        err("auth_error", "no API key found", 3)
    if mode == "oauth":
        out({"data": {"source": "oauth", "expires_at": "2026-11-01T00:00:00Z", "refreshable": True}})
    out({"data": {"key_name": "heditor", "permission_mode": "full"}})
if args[:3] == ["user", "me", "get"]:
    if mode == "oauth":
        out({"data": {"username": "felipe", "email": "f@example.com", "first_name": "F", "last_name": "A",
                      "billing_type": "subscription",
                      "subscription": {"plan": "creator", "credits": {
                          "premium_credits": {"remaining": 600, "resets_at": "2026-11-20"},
                          "add_on_credits": {"remaining": 0}}}}})
    out({"data": {"username": "felipe", "email": "f@example.com", "first_name": "F", "last_name": "A",
                  "billing_type": "wallet", "wallet": {"currency": "usd", "remaining_balance": 25.5}}})
LOOK = {"id": "look1", "name": "Felipe studio", "avatar_type": "digital_twin",
        "default_voice_id": os.environ.get("FAKE_LOOK_VOICE", "voice1"),
        "preferred_orientation": os.environ.get("FAKE_ORIENTATION", "portrait"), "status": "completed",
        "supported_api_engines": ["avatar_v", "avatar_iv"]}
if args[:3] == ["avatar", "looks", "get"]:
    out({"data": LOOK})
if args[:3] == ["avatar", "looks", "list"]:
    out({"data": [LOOK], "has_more": False})
if args[:2] == ["voice", "list"]:
    out({"data": [{"voice_id": "voice1", "name": "Felipe", "language": "Portuguese", "gender": "male",
                   "type": "private", "available_engines": ["orca"], "support_pause": True,
                   "support_locale": False}], "has_more": False})
if args[:3] == ["brand", "glossaries", "list"]:
    out({"data": [{"brand_glossary_id": "gl1", "name": "Pronúncia"}], "has_more": False})
if args[:3] == ["brand", "glossaries", "get"]:
    out({"data": {"brand_glossary_id": args[3], "name": "Pronúncia",
                  "terms": [{"term": "Python", "pronunciation": "páiton"}]}})
if args[:2] == ["asset", "create"]:
    out({"data": {"asset_id": "asset1", "url": "https://x/a.wav", "mime_type": "audio/wav", "size_bytes": 10}})
if args[:2] == ["video", "create"]:
    out({"data": {"video_id": "vid1", "status": "waiting"}})
if args[:2] == ["video", "get"]:
    out({"data": {"id": args[2], "status": os.environ.get("FAKE_VIDEO_STATUS", "completed"), "duration": 3.0,
                  "video_url": "https://x/v.mp4"}})
if args[:2] == ["video", "download"]:
    dest = args[args.index("--output-path") + 1]
    shutil.copy(os.environ["FAKE_MP4"], dest)
    out({"asset": "video", "message": "Downloaded", "path": dest})
if args[:3] == ["auth", "login", "--oauth"]:
    import http.server, urllib.parse
    result = {}
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            result.update(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query))
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        def log_message(self, *a):
            pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    redirect = urllib.parse.quote(f"http://127.0.0.1:{port}/oauth/callback", safe="")
    print("Opening browser to https://app.heygen.com/oauth/authorize ...")
    print("Open this URL manually to continue:")
    print(f"  https://app.heygen.com/oauth/authorize?client_id=x&redirect_uri={redirect}&state=st4te", flush=True)
    srv.handle_request()
    if result.get("code") == ["good"] and result.get("state") == ["st4te"]:
        open(flag, "w").write("1")
        out({"data": {"message": "logged in"}})
    err("error", "token exchange failed", 1)
if args[:2] == ["auth", "logout"]:
    out({"data": {"message": "logged out"}})
err("usage_error", "unexpected " + " ".join(args), 2)
'''


@pytest.fixture(scope="session")
def tiny_mp4(tmp_path_factory):
    path = tmp_path_factory.mktemp("media") / "tiny.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=108x192:rate=30:duration=1",
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


@pytest.fixture
def fake(tmp_path, monkeypatch, tiny_mp4):
    cli = tmp_path / "bin" / "heygen"
    cli.parent.mkdir()
    cli.write_text(FAKE_CLI)
    cli.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("HEYGEN_BIN", str(cli))
    monkeypatch.setenv("FAKE_LOG", str(log))
    monkeypatch.setenv("FAKE_MP4", str(tiny_mp4))
    monkeypatch.setenv("FAKE_MODE", "oauth")
    monkeypatch.setenv("HEDITOR_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HEDITOR_LANG", "en")
    monkeypatch.delenv("HEYGEN_API_KEY", raising=False)

    def calls():
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()]

    return calls


def _avatar(work, *extra):
    return heygenkit.main(["avatar", str(work), *extra])


# ---------------------------------------------------------------- status

def test_not_installed_is_optional(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HEYGEN_BIN", str(tmp_path / "missing"))
    monkeypatch.setenv("HEDITOR_LANG", "en")
    status = heygenkit.account_status()
    assert status["installed"] is False and status["connected"] is False
    assert heygenkit.main(["status"]) == heygenkit.EXIT_AUTH
    assert "not connected" in capsys.readouterr().out


def test_status_not_connected(fake, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_MODE", "none")
    assert heygenkit.main(["status"]) == heygenkit.EXIT_AUTH
    assert "heditor heygen connect" in capsys.readouterr().out


def test_status_oauth_uses_subscription_credits(fake, capsys):
    status = heygenkit.account_status()
    assert status["connected"] and status["auth"] == "oauth" and status["billing"] == "subscription"
    assert status["plan"] == "creator" and status["premium_credits"] == 600
    assert heygenkit.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "subscription credits" in out and "600" in out


def test_status_api_key_uses_wallet(fake, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_MODE", "apikey")
    monkeypatch.setenv("HEYGEN_API_KEY", SECRET)
    status = heygenkit.account_status()
    assert status["auth"] == "api_key" and status["wallet_balance"] == 25.5
    assert heygenkit.main(["status", "--json"]) == 0
    out = capsys.readouterr().out
    assert SECRET not in out
    assert all(SECRET not in " ".join(c["args"]) for c in fake())


def test_auth_kind_falls_back_to_billing():
    assert heygenkit._auth_kind({}, "subscription") == "oauth"
    assert heygenkit._auth_kind({}, "wallet") == "api_key"
    assert heygenkit._auth_kind({"data": {"credential": {"type": "OAuth"}}}, None) == "oauth"
    assert heygenkit._auth_kind(None, None) == "unknown"


def test_language_from_brand(monkeypatch, tmp_path):
    monkeypatch.delenv("HEDITOR_LANG", raising=False)
    monkeypatch.setenv("HEDITOR_HOME", str(tmp_path))
    assert heygenkit.lang() == "en"
    (tmp_path / "brand.json").write_text(json.dumps({"lang": "pt"}))
    assert heygenkit.lang() == "pt"
    assert "créditos" in heygenkit.msg("auth_oauth")


# ---------------------------------------------------------------- connect / disconnect

def test_connect_refuses_without_terminal(fake, monkeypatch, capsys):
    monkeypatch.setattr(heygenkit, "interactive", lambda: False)
    assert heygenkit.main(["connect"]) == heygenkit.EXIT_USAGE
    out = capsys.readouterr().out
    assert "heygen auth login --oauth" in out and "connect --remote" in out and "--api-key" in out
    assert fake() == []


def test_connect_menu_uses_the_remote_flow_on_servers(fake, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("FAKE_MODE", "none")
    monkeypatch.setenv("FAKE_LOGGED_FILE", str(tmp_path / "logged"))
    monkeypatch.setattr(heygenkit, "interactive", lambda: True)
    monkeypatch.setattr(heygenkit, "is_remote", lambda: True)
    monkeypatch.setattr(heygenkit, "run_interactive", lambda args: pytest.fail("no local browser on a server"))
    printed = []
    real_print = print

    def spy(*a, **k):
        printed.append(" ".join(str(x) for x in a))
        real_print(*a, **k)

    def port():
        line = next(p for p in printed if "oauth/authorize" in p)
        return int(re.search(r"127\.0\.0\.1%3A(\d+)", line).group(1))

    answers = iter(["1", "http://example.com/whatever",
                    lambda: f"http://127.0.0.1:{port()}/oauth/callback?code=good&state=other",
                    lambda: f"http://127.0.0.1:{port()}/oauth/callback?code=good&state=st4te"])

    def answer(prompt=""):
        value = next(answers)
        return value() if callable(value) else value

    monkeypatch.setattr("builtins.print", spy)
    monkeypatch.setattr("builtins.input", answer)
    assert heygenkit.main(["connect"]) == 0
    out = "\n".join(printed)
    assert "127.0.0.1" in out and "another login attempt" in out and "must start with" in out
    assert "Connected." in out and "subscription credits" in out


def test_callback_target_validation():
    redirect = "http://127.0.0.1:4000/oauth/callback"
    ok, problem = heygenkit._callback_target("http://localhost:4000/oauth/callback?code=c&state=s", redirect, "s")
    assert problem is None and ok == "http://127.0.0.1:4000/oauth/callback?code=c&state=s"
    assert heygenkit._callback_target("http://127.0.0.1:4001/oauth/callback?code=c&state=s", redirect, "s")[1] \
        == "remote_bad"
    assert heygenkit._callback_target("http://evil.com:4000/oauth/callback?code=c&state=s", redirect, "s")[1] \
        == "remote_bad"
    assert heygenkit._callback_target("http://127.0.0.1:4000/oauth/callback?code=c&state=x", redirect, "s")[1] \
        == "remote_state"
    assert heygenkit._callback_target("http://127.0.0.1:4000/oauth/callback?error=access_denied&state=s",
                                      redirect, "s")[1] is None


def test_connect_api_key_is_typed_into_the_heygen_cli(fake, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "none")
    monkeypatch.setattr(heygenkit, "interactive", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "2")
    seen = []

    def login(args):
        seen.append(args)
        os.environ["FAKE_MODE"] = "apikey"
        return 0

    monkeypatch.setattr(heygenkit, "run_interactive", login)
    assert heygenkit.main(["connect"]) == 0
    assert seen == [["auth", "login", "--api-key"]]


def test_connect_cancel_changes_nothing(fake, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "none")
    monkeypatch.setattr(heygenkit, "interactive", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "3")
    monkeypatch.setattr(heygenkit, "run_interactive", lambda args: pytest.fail("must not log in"))
    assert heygenkit.main(["connect"]) == 0


def test_disconnect_needs_confirmation(fake, monkeypatch):
    monkeypatch.setattr(heygenkit, "interactive", lambda: False)
    assert heygenkit.main(["disconnect"]) == heygenkit.EXIT_USAGE
    assert not any(c["args"][:2] == ["auth", "logout"] for c in fake())
    assert heygenkit.main(["disconnect", "--yes"]) == 0
    assert any(c["args"][:2] == ["auth", "logout"] for c in fake())


# ---------------------------------------------------------------- estimate

def test_cost_estimates():
    sub = heygenkit.estimate_cost("avatar_v", "digital_twin", 60, "subscription")
    assert sub["unit"] == "credits" and sub["amount"] == 48
    assert heygenkit.estimate_cost("avatar_v", "photo_avatar", 60, "subscription")["amount"] == 48
    api = heygenkit.estimate_cost("avatar_iv", "digital_twin", 60, "wallet")
    assert api["unit"] == "usd" and api["amount"] == 4.83
    assert heygenkit.estimate_cost("avatar_iii", "digital_twin", 60, "subscription")["amount"] is None
    assert "check the HeyGen dashboard" in heygenkit.format_cost(
        heygenkit.estimate_cost("avatar_iii", "digital_twin", 60, "subscription"))
    assert heygenkit.script_seconds("um dois tres quatro cinco seis sete oito nove dez " * 13) == 50.0
    paused = 'Primeiro ponto. <break time="0.5s"/> Segundo ponto. <break time="1s"/>'
    assert heygenkit.script_seconds(paused) == round(4 / heygenkit.WORDS_PER_SECOND + 1.5, 1)
    assert heygenkit.script_seconds("um dois tres quatro cinco seis sete oito nove dez " * 13, 1.25) == 40.0


def test_break_tags_must_use_seconds():
    heygenkit.check_breaks('Olá. <break time="0.35s"/> Tudo bem?')
    with pytest.raises(heygenkit.HeyGenError) as exc:
        heygenkit.check_breaks('Olá. <break time="350ms"/> Tudo bem?')
    assert exc.value.code == heygenkit.EXIT_USAGE


# ---------------------------------------------------------------- avatar video

def test_avatar_dry_run_spends_nothing(fake, tmp_path, capsys):
    assert _avatar(tmp_path / "w", "--look", "look1", "--text", "Olá, pessoal.", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "premium credits" in out and '"engine"' in out and "avatar_v" in out
    assert not any(c["args"][:2] in (["video", "create"], ["asset", "create"]) for c in fake())


def test_avatar_needs_approval_without_terminal(fake, tmp_path, monkeypatch):
    monkeypatch.setattr(heygenkit, "interactive", lambda: False)
    assert _avatar(tmp_path / "w", "--look", "look1", "--text", "Olá.") == heygenkit.EXIT_USAGE
    assert not any(c["args"][:2] == ["video", "create"] for c in fake())


def test_avatar_from_script(fake, tmp_path, capsys):
    work = tmp_path / "w"
    script = tmp_path / "roteiro.txt"
    script.write_text("Hoje eu vou mostrar como o agente revisa o próprio código.\n", encoding="utf-8")
    assert _avatar(work, "--look", "look1", "--script", str(script), "--yes") == 0
    create = [c for c in fake() if c["args"][:2] == ["video", "create"]]
    assert len(create) == 1
    req = json.loads(create[0]["stdin"])
    assert req["avatar_id"] == "look1" and req["engine"] == {"type": "avatar_v"}
    assert req["script"].startswith("Hoje eu vou") and req["voice_id"] == "voice1"
    assert req["aspect_ratio"] == "9:16" and "audio_asset_id" not in req
    key = create[0]["args"][create[0]["args"].index("--idempotency-key") + 1]
    assert key.startswith("heditor-")
    data = json.loads((work / "avatar.json").read_text())
    entry = data["generations"][0]
    assert entry["video_id"] == "vid1" and entry["status"] == "downloaded" and entry["synthetic"] is True
    assert entry["billing"] == "subscription" and entry["estimated_cost"]["unit"] == "credits"
    assert (entry["width"], entry["height"]) == (108, 192) and len(entry["sha256"]) == 64
    assert Path(entry["file"]).exists() and Path(entry["script_file"]).read_text().startswith("Hoje")
    assert f"heditor new {work}" in capsys.readouterr().out


def test_avatar_from_audio_uploads_it(fake, tmp_path, monkeypatch, tiny_mp4):
    monkeypatch.setenv("FAKE_MODE", "apikey")
    audio = tmp_path / "voz.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
                    str(audio)], check=True)
    assert _avatar(tmp_path / "w", "--look", "look1", "--audio", str(audio), "--engine", "iv", "--yes") == 0
    calls = fake()
    assert any(c["args"][:2] == ["asset", "create"] for c in calls)
    req = json.loads(next(c for c in calls if c["args"][:2] == ["video", "create"])["stdin"])
    assert req["audio_asset_id"] == "asset1" and "script" not in req and req["engine"] == {"type": "avatar_iv"}
    entry = json.loads((tmp_path / "w" / "avatar.json").read_text())["generations"][0]
    assert entry["input"] == "audio" and entry["estimated_cost"]["unit"] == "usd"


def test_avatar_glossary_and_speed_go_into_the_request(fake, tmp_path, capsys):
    script = tmp_path / "roteiro.txt"
    script.write_text('Eu uso Python com o Hermes. <break time="0.4s"/> E faço o deploy.\n', encoding="utf-8")
    assert _avatar(tmp_path / "w", "--look", "look1", "--script", str(script), "--glossary", "gl1",
                   "--speed", "1.05", "--yes") == 0
    req = json.loads(next(c for c in fake() if c["args"][:2] == ["video", "create"])["stdin"])
    assert req["brand_glossary_id"] == "gl1" and req["voice_settings"] == {"speed": 1.05}
    assert '<break time="0.4s"/>' in req["script"]
    entry = json.loads((tmp_path / "w" / "avatar.json").read_text())["generations"][0]
    assert entry["glossary_id"] == "gl1" and entry["speed"] == 1.05
    assert "glossary: gl1" in capsys.readouterr().out


def test_avatar_without_glossary_says_so(fake, tmp_path, capsys):
    assert _avatar(tmp_path / "w", "--look", "look1", "--text", "Olá.", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "glossary: none" in out and "brand_glossary_id" not in out and "voice_settings" not in out


def test_avatar_glossary_and_speed_reject_audio_and_bad_values(fake, tmp_path):
    audio = tmp_path / "voz.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=1",
                    str(audio)], check=True)
    with pytest.raises(heygenkit.HeyGenError) as exc:
        _avatar(tmp_path / "w", "--look", "look1", "--audio", str(audio), "--glossary", "gl1", "--dry-run")
    assert exc.value.code == heygenkit.EXIT_USAGE
    with pytest.raises(heygenkit.HeyGenError):
        _avatar(tmp_path / "w", "--look", "look1", "--text", "Olá.", "--speed", "2", "--dry-run")
    with pytest.raises(heygenkit.HeyGenError):
        _avatar(tmp_path / "w", "--look", "look1", "--text", 'Olá. <break time="300ms"/>', "--dry-run")
    assert not any(c["args"][:2] == ["video", "create"] for c in fake())


def test_glossaries_list_terms(fake, capsys):
    assert heygenkit.main(["glossaries"]) == 0
    out = capsys.readouterr().out
    assert "gl1" in out and "Python  ->  páiton" in out


def test_avatar_never_uses_a_stock_default_voice(fake, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_LOOK_VOICE", "stock_voice_9")  # HeyGen returns a stock voice for photo looks
    with pytest.raises(heygenkit.HeyGenError) as exc:
        _avatar(tmp_path / "w", "--look", "look1", "--text", "Olá.", "--dry-run")
    assert exc.value.code == heygenkit.EXIT_USAGE and "not one of your cloned voices" in str(exc.value)
    assert _avatar(tmp_path / "w", "--look", "look1", "--text", "Olá.", "--voice", "voice1", "--dry-run") == 0


def test_avatar_uses_the_brand_voice(fake, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_LOOK_VOICE", "stock_voice_9")
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    (home / "brand.json").write_text(json.dumps({"lang": "pt", "heygen": {"voice_id": "voice1"}}), encoding="utf-8")
    monkeypatch.setenv("HEDITOR_HOME", str(home))
    monkeypatch.setenv("HEDITOR_LANG", "en")
    assert _avatar(tmp_path / "w", "--look", "look1", "--text", "Olá.", "--yes") == 0
    req = json.loads(next(c for c in fake() if c["args"][:2] == ["video", "create"])["stdin"])
    assert req["voice_id"] == "voice1"
    assert "brand.json heygen.voice_id" in capsys.readouterr().out


def test_idempotency_key_is_stable():
    req = heygenkit.build_request("look1", "avatar_v", "9:16", "1080p", "t", script="Olá", voice_id="v")
    assert heygenkit.idempotency_key(req, "abc") == heygenkit.idempotency_key(dict(req), "abc")
    assert heygenkit.idempotency_key(req, "abc") != heygenkit.idempotency_key(req, "abd")


def test_avatar_rejects_unsupported_engine(fake, tmp_path):
    with pytest.raises(heygenkit.HeyGenError) as exc:
        _avatar(tmp_path / "w", "--look", "look1", "--text", "Olá.", "--engine", "iii", "--dry-run")
    assert exc.value.code == heygenkit.EXIT_USAGE


def test_avatar_requires_connection(fake, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "none")
    with pytest.raises(heygenkit.HeyGenError) as exc:
        _avatar(tmp_path / "w", "--look", "look1", "--text", "Olá.", "--dry-run")
    assert exc.value.code == heygenkit.EXIT_AUTH


def test_avatar_timeout_can_resume(fake, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_VIDEO_STATUS", "processing")
    monkeypatch.setattr(heygenkit.time, "sleep", lambda s: None)
    work = tmp_path / "w"
    assert _avatar(work, "--look", "look1", "--text", "Olá.", "--yes", "--timeout", "1s") == heygenkit.EXIT_TIMEOUT
    assert json.loads((work / "avatar.json").read_text())["generations"][0]["status"] == "rendering"
    monkeypatch.setenv("FAKE_VIDEO_STATUS", "completed")
    assert _avatar(work, "--resume", "vid1") == 0
    entry = json.loads((work / "avatar.json").read_text())["generations"][0]
    assert entry["status"] == "downloaded" and entry["look_id"] == "look1"


def test_avatar_warns_on_landscape_look(fake, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_ORIENTATION", "landscape")
    assert _avatar(tmp_path / "w", "--look", "look1", "--text", "Olá.", "--dry-run") == 0
    assert "landscape" in capsys.readouterr().out


def test_lists(fake, capsys):
    assert heygenkit.main(["avatars"]) == 0
    assert heygenkit.main(["voices"]) == 0
    out = capsys.readouterr().out
    assert "look1" in out and "engines=v,iv" in out and "voice1" in out


def test_cli_help_mentions_the_optional_commands():
    script = Path(__file__).resolve().parents[1] / "heditor"
    out = subprocess.run(["bash", str(script), "help"], capture_output=True, text=True,
                         env=dict(os.environ, HEDITOR_HOME="/nonexistent")).stdout
    assert "heditor heygen connect" in out and "heditor avatar <work>" in out and "glossaries" in out
