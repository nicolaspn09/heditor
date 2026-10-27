#!/usr/bin/env python3
"""heygenkit: optional HeyGen connection and AI avatar source videos for heditor.

Nothing here is needed for the rest of heditor. It drives the official HeyGen CLI (`heygen`), which owns the
credentials: heditor never reads, prints, stores or passes a key on the command line. Two ways to connect:

- HeyGen account (OAuth): videos use the credits of the user's HeyGen subscription. Browser login on a desktop; on
  a server or over SSH (`--remote`) the person approves on any computer and pastes the return address.
- API key: videos are billed to the prepaid HeyGen API wallet. The key is typed into the HeyGen CLI's hidden prompt.

CLI (through `heditor`):
  heditor heygen connect [--oauth|--remote|--device|--api-key] [--install]   interactive, by the account owner
  heditor heygen status [--json]                                     account, billing mode, plan, credits/balance
  heditor heygen disconnect [--yes]
  heditor heygen avatars [--json]                                    your avatar looks (ids, engines, orientation)
  heditor heygen voices [--json]                                     your cloned voices
  heditor heygen glossaries [--json]                                 pronunciation glossaries and their terms
  heditor avatar <work> --look ID (--script FILE | --text "..." | --audio FILE) [--voice ID] [--engine v|iv|iii]
                 [--glossary ID] [--speed 0.5-1.5] [--aspect 9:16] [--resolution 1080p] [--motion "..."]
                 [--title T] [--dry-run] [--yes]
  heditor avatar <work> --resume VIDEO_ID                            download a video that was still rendering
"""
import argparse
import hashlib
import json
import os
import pty
import select
import shutil
import subprocess
import sys
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

INSTALL_URL = "https://static.heygen.ai/cli/install.sh"
API_KEYS_URL = "https://app.heygen.com/settings?nav=API"
DOCS_URL = "https://developers.heygen.com/cli"
WORDS_PER_SECOND = 2.6  # conversational PT/EN speech; only for the cost estimate of a script
ENGINES = {"v": "avatar_v", "iv": "avatar_iv", "iii": "avatar_iii",
           "avatar_v": "avatar_v", "avatar_iv": "avatar_iv", "avatar_iii": "avatar_iii"}
# Published rates when this version shipped (HeyGen help centre and API pricing, Oct 2026). HeyGen changes them
# without notice: they are an estimate shown before asking for approval, never the amount billed.
RATES_AS_OF = "2026-10"
CREDITS_PER_MIN = {  # subscription (OAuth) premium credits per minute
    ("avatar_v", "digital_twin"): 48, ("avatar_v", "studio_avatar"): 48, ("avatar_v", "photo_avatar"): 48,
    ("avatar_iv", "digital_twin"): 31, ("avatar_iv", "studio_avatar"): 31, ("avatar_iv", "photo_avatar"): 16,
}
USD_PER_MIN = {  # API wallet, USD per minute
    ("avatar_v", "digital_twin"): 7.20, ("avatar_v", "studio_avatar"): 7.20,
    ("avatar_iv", "digital_twin"): 4.83, ("avatar_iv", "studio_avatar"): 4.83, ("avatar_iv", "photo_avatar"): 2.31,
    ("avatar_iii", "digital_twin"): 0.60, ("avatar_iii", "studio_avatar"): 0.99, ("avatar_iii", "photo_avatar"): 0.99,
}
EXIT_USAGE, EXIT_AUTH, EXIT_TIMEOUT = 2, 3, 4

MESSAGES = {
    "pt": {
        "title": "Conectar a HeyGen ao heditor (opcional)",
        "intro": ("O heditor usa o CLI oficial da HeyGen. A credencial fica com o CLI da HeyGen "
                  "(~/.heygen/credentials); o heditor não lê nem guarda a sua chave."),
        "need_tty": ("Este assistente é interativo e precisa ser executado pela pessoa dona da conta, num terminal.\n"
                     "Rode no seu terminal:\n  heditor heygen connect\n"
                     "Ou diretamente:\n  heygen auth login --oauth    (conta HeyGen, créditos da assinatura)\n"
                     "  heditor heygen connect --remote  (conta HeyGen num servidor/SSH)\n"
                     "  heygen auth login --api-key  (chave de API, carteira da API)"),
        "missing_cli": "O CLI da HeyGen (heygen) não está instalado.",
        "ask_install": (f"Instalar agora com o instalador oficial ({INSTALL_URL}, confere o checksum, "
                        "vai para ~/.local/bin)? [s/N] "),
        "install_hint": f"Instale com: curl -fsSL {INSTALL_URL} | bash   (ou rode: heditor heygen connect --install)",
        "installed": "CLI da HeyGen instalado: {path}",
        "already": "Já existe uma conexão: {desc}. Conectar de novo substitui essa credencial.",
        "ask_replace": "Substituir? [s/N] ",
        "env_key": ("Atenção: a variável HEYGEN_API_KEY está definida e tem prioridade sobre o login salvo. "
                    "Para usar a conta HeyGen (OAuth), remova-a do ambiente."),
        "menu": ("Como você quer conectar?\n"
                 "  1) Conta HeyGen (OAuth): os vídeos usam os créditos da sua assinatura HeyGen.\n"
                 "     Indicado para quem já assina. A HeyGen recomenda para testes e volume baixo.\n"
                 "  2) Chave de API: os vídeos são cobrados na carteira pré-paga da API HeyGen (em dólar).\n"
                 "     Indicado para produção em lote. Gere a chave em " + API_KEYS_URL + "\n"
                 "  3) Cancelar"),
        "ask_choice": "Escolha [1/2/3]: ",
        "remote": ("Você está num servidor ou via SSH, então o navegador não abre aqui. Vamos fazer em três passos:\n"
                   "  1. Abra no navegador do seu computador o link abaixo, entre na HeyGen e aprove o acesso.\n"
                   "  2. Depois de aprovar, o navegador mostra uma página de erro em 127.0.0.1. Isso é esperado.\n"
                   "  3. Copie o endereço completo da barra do navegador (começa com http://127.0.0.1) e cole aqui."),
        "remote_paste": "Cole o endereço (ou deixe vazio para cancelar): ",
        "remote_bad": "Esse endereço não é o retorno deste login (precisa começar com {prefix}). Tente de novo.",
        "remote_state": ("Esse endereço é de outra tentativa de login. "
                         "Abra o link acima de novo e cole o novo endereço."),
        "remote_denied": "A HeyGen não autorizou o acesso ({error}).",
        "browser": "O navegador vai abrir para você entrar na HeyGen e aprovar o acesso.",
        "key_prompt": "Cole a chave quando o CLI pedir. A digitação fica oculta e a chave não passa pelo heditor.",
        "cancelled": "Cancelado. Nada foi alterado.",
        "failed": "O login não foi concluído (código {rc}). Nada foi alterado no heditor.",
        "connected": "Conectado.",
        "not_connected": "HeyGen não conectada. Para conectar (opcional): heditor heygen connect",
        "status_auth": "Conexão: {auth}",
        "auth_oauth": "conta HeyGen (OAuth), créditos da assinatura",
        "auth_api_key": "chave de API, carteira da API",
        "auth_unknown": "credencial ativa (tipo não informado)",
        "status_user": "Conta: {user}",
        "status_plan": "Plano: {plan}",
        "status_credits": "Créditos premium restantes: {n}{reset}",
        "status_addon": "Créditos adicionais restantes: {n}",
        "status_wallet": "Saldo da carteira da API: {bal}",
        "status_usage": "Uso medido: {spent} de limite {cap}",
        "disconnect_ask": "Desconectar a HeyGen (remove a credencial salva pelo CLI da HeyGen)? [s/N] ",
        "disconnected": "Desconectado.",
        "confirm": "Gerar este vídeo? [s/N] ",
        "need_yes": ("Sem terminal interativo: mostre a estimativa a quem paga e, com a aprovação, "
                     "rode de novo com --yes."),
        "yes": ("s", "sim", "y", "yes"),
    },
    "en": {
        "title": "Connect HeyGen to heditor (optional)",
        "intro": ("heditor uses the official HeyGen CLI. The credential stays with the HeyGen CLI "
                  "(~/.heygen/credentials); heditor never reads or stores your key."),
        "need_tty": ("This assistant is interactive and must be run by the account owner, in a terminal.\n"
                     "Run in your terminal:\n  heditor heygen connect\n"
                     "Or directly:\n  heygen auth login --oauth    (HeyGen account, subscription credits)\n"
                     "  heditor heygen connect --remote  (HeyGen account on a server/SSH)\n"
                     "  heygen auth login --api-key  (API key, API wallet)"),
        "missing_cli": "The HeyGen CLI (heygen) is not installed.",
        "ask_install": (f"Install it now with the official installer ({INSTALL_URL}, checksum verified, "
                        "into ~/.local/bin)? [y/N] "),
        "install_hint": f"Install with: curl -fsSL {INSTALL_URL} | bash   (or run: heditor heygen connect --install)",
        "installed": "HeyGen CLI installed: {path}",
        "already": "A connection already exists: {desc}. Connecting again replaces that credential.",
        "ask_replace": "Replace it? [y/N] ",
        "env_key": ("Warning: HEYGEN_API_KEY is set and takes priority over the stored login. "
                    "Unset it to use the HeyGen account (OAuth)."),
        "menu": ("How do you want to connect?\n"
                 "  1) HeyGen account (OAuth): videos use the credits of your HeyGen subscription.\n"
                 "     Best if you already subscribe. HeyGen recommends it for tests and low volume.\n"
                 "  2) API key: videos are billed to the prepaid HeyGen API wallet (USD).\n"
                 "     Best for batch production. Create the key at " + API_KEYS_URL + "\n"
                 "  3) Cancel"),
        "ask_choice": "Choose [1/2/3]: ",
        "remote": ("You are on a server or over SSH, so no browser opens here. Three steps:\n"
                   "  1. Open the link below in your computer's browser, sign in to HeyGen and approve access.\n"
                   "  2. After approving, the browser shows an error page on 127.0.0.1. That is expected.\n"
                   "  3. Copy the full address from the browser bar (it starts with http://127.0.0.1) and paste "
                   "it here."),
        "remote_paste": "Paste the address (or leave empty to cancel): ",
        "remote_bad": "That address is not the return of this login (it must start with {prefix}). Try again.",
        "remote_state": ("That address belongs to another login attempt. "
                         "Open the link above again and paste the new one."),
        "remote_denied": "HeyGen did not authorize access ({error}).",
        "browser": "Your browser will open so you can sign in to HeyGen and approve access.",
        "key_prompt": "Paste the key when the CLI asks. Input is hidden and the key never passes through heditor.",
        "cancelled": "Cancelled. Nothing was changed.",
        "failed": "Login did not complete (code {rc}). Nothing was changed in heditor.",
        "connected": "Connected.",
        "not_connected": "HeyGen is not connected. To connect (optional): heditor heygen connect",
        "status_auth": "Connection: {auth}",
        "auth_oauth": "HeyGen account (OAuth), subscription credits",
        "auth_api_key": "API key, API wallet",
        "auth_unknown": "active credential (type not reported)",
        "status_user": "Account: {user}",
        "status_plan": "Plan: {plan}",
        "status_credits": "Premium credits left: {n}{reset}",
        "status_addon": "Add-on credits left: {n}",
        "status_wallet": "API wallet balance: {bal}",
        "status_usage": "Metered usage: {spent} of cap {cap}",
        "disconnect_ask": "Disconnect HeyGen (removes the credential stored by the HeyGen CLI)? [y/N] ",
        "disconnected": "Disconnected.",
        "confirm": "Generate this video? [y/N] ",
        "need_yes": "No interactive terminal: show the estimate to whoever pays and, once approved, re-run with --yes.",
        "yes": ("y", "yes", "s", "sim"),
    },
}


class HeyGenError(RuntimeError):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------- environment

def heditor_home():
    return Path(os.environ.get("HEDITOR_HOME", "~/.heditor")).expanduser()


def lang():
    """Language of the interactive texts: HEDITOR_LANG, else brand.json `lang`, else English."""
    value = os.environ.get("HEDITOR_LANG", "")
    if not value:
        brand = heditor_home() / "brand.json"
        try:
            data = json.loads(brand.read_text(encoding="utf-8"))
            value = data.get("lang") or data.get("language") or ""
        except (OSError, ValueError):
            value = ""
    return "pt" if str(value).lower().startswith("pt") else "en"


def brand_voice():
    """The user's official voice for every avatar video: brand.json `heygen.voice_id` (or HEDITOR_HEYGEN_VOICE)."""
    value = os.environ.get("HEDITOR_HEYGEN_VOICE", "")
    if not value:
        try:
            data = json.loads((heditor_home() / "brand.json").read_text(encoding="utf-8"))
            value = (data.get("heygen") or {}).get("voice_id") or ""
        except (OSError, ValueError, AttributeError):
            value = ""
    return value.strip() or None


def resolve_voice(explicit, look):
    """Voice for a script: --voice, else the brand voice, else the look's default only if it is one of the
    account's cloned voices. A look's default voice can be a stock voice (HeyGen returns one for photo looks),
    and a stock voice speaking as the person is the worst possible mistake, so it is never used silently."""
    if explicit:
        return explicit, "--voice"
    brand = brand_voice()
    if brand:
        return brand, "brand.json heygen.voice_id"
    default = look.get("default_voice_id")
    cloned = {v.get("voice_id") for v in list_voices()}
    if default and default in cloned:
        return default, "look default (one of your cloned voices)"
    raise HeyGenError(
        f"the look's default voice ({default or 'none'}) is not one of your cloned voices: pass --voice ID "
        "(heditor heygen voices) or set your official voice once in ~/.heditor/brand.json as "
        '"heygen": {"voice_id": "<id>"}', EXIT_USAGE)


def msg(key, **kw):
    text = MESSAGES[lang()][key]
    return text.format(**kw) if kw else text


def interactive():
    return sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get("HEYGEN_NONINTERACTIVE") != "1" \
        and os.environ.get("CI", "").lower() != "true"


def ask_yes(prompt):
    try:
        return input(prompt).strip().lower() in MESSAGES[lang()]["yes"]
    except EOFError:
        return False


def is_remote():
    """True when a browser on this machine is unlikely: SSH session or a Linux box without a display."""
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return True
    if sys.platform.startswith("linux"):
        return not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return False


def find_cli():
    explicit = os.environ.get("HEYGEN_BIN")
    if explicit:
        return explicit if Path(explicit).exists() else None
    found = shutil.which("heygen")
    if found:
        return found
    local = Path("~/.local/bin/heygen").expanduser()
    return str(local) if local.exists() else None


# ---------------------------------------------------------------- running the HeyGen CLI

def _parse_json(text):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        pass
    # Notices (telemetry, updates) may precede the payload: take the last line that parses.
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith(("{", "[")):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return None


def run_cli(args, stdin=None, timeout=120):
    """Run `heygen <args>` capturing JSON. Returns (returncode, parsed stdout, parsed stderr error dict)."""
    cli = find_cli()
    if not cli:
        raise HeyGenError(msg("missing_cli") + "\n" + msg("install_hint"), EXIT_AUTH)
    env = dict(os.environ, HEYGEN_OUTPUT="json")
    proc = subprocess.run([cli, *args], input=stdin, capture_output=True, text=True, timeout=timeout, env=env)
    err = _parse_json(proc.stderr) or {}
    return proc.returncode, _parse_json(proc.stdout), (err.get("error") if isinstance(err, dict) else None) or {}


def cli_json(args, stdin=None, timeout=120):
    rc, out, err = run_cli(args, stdin=stdin, timeout=timeout)
    if rc != 0:
        if rc == EXIT_AUTH:
            detail = "" if err.get("code") == "auth_error" else (err.get("message") or "")
            raise HeyGenError(msg("not_connected") + (f" ({detail})" if detail else ""), EXIT_AUTH)
        text = err.get("message") or f"heygen {' '.join(args[:3])} failed (exit {rc})"
        if err.get("hint"):
            text += "\n" + err["hint"]
        raise HeyGenError(text, rc if rc == EXIT_TIMEOUT else 1)
    return out if isinstance(out, dict) else {}


def run_interactive(args):
    """Hand the terminal to the HeyGen CLI (login prompts, browser, device code). Nothing is captured."""
    cli = find_cli()
    if not cli:
        raise HeyGenError(msg("missing_cli") + "\n" + msg("install_hint"), EXIT_AUTH)
    return subprocess.run([cli, *args]).returncode


def install_cli():
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "install.sh"
        req = urllib.request.Request(INSTALL_URL, headers={"User-Agent": "heditor"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            script.write_bytes(resp.read())
        rc = subprocess.run(["bash", str(script)]).returncode
    if rc != 0 or not find_cli():
        raise HeyGenError(msg("install_hint"))
    return find_cli()


# ---------------------------------------------------------------- account status

AUTH_KEYS = ("type", "source", "auth_type", "credential_type", "method", "kind", "credential")


def _auth_kind(auth, billing):
    """'oauth', 'api_key' or 'unknown' from `heygen auth status` output, falling back to the billing type."""
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and key.lower() in AUTH_KEYS:
                    low = value.lower()
                    if "oauth" in low:
                        return "oauth"
                    if "api" in low and "key" in low:
                        return "api_key"
                found = walk(value)
                if found:
                    return found
            if any("oauth" in str(k).lower() for k in node):
                return "oauth"
            if any(str(k).lower() in ("key_name", "api_key", "scopes_mode", "permission_mode") for k in node):
                return "api_key"
        elif isinstance(node, list):
            for item in node:
                found = walk(item)
                if found:
                    return found
        return None

    kind = walk(auth or {})
    if kind:
        return kind
    return {"subscription": "oauth", "wallet": "api_key", "usage_based": "api_key"}.get(billing or "", "unknown")


def account_status():
    """Connection, billing mode and balance. Never includes secrets."""
    status: dict = {"installed": bool(find_cli()), "connected": False,
                    "env_api_key": bool(os.environ.get("HEYGEN_API_KEY"))}
    if not status["installed"]:
        return status
    status["cli_version"] = _version_text()
    rc, auth, err = run_cli(["auth", "status"], timeout=60)
    if rc != 0:
        status["error"] = err.get("code") or f"exit {rc}"
        return status
    status["connected"] = True
    try:
        me = (cli_json(["user", "me", "get"], timeout=60).get("data") or {})
    except HeyGenError as exc:
        me = {}
        status["error"] = str(exc).splitlines()[0]
    billing = me.get("billing_type")
    status.update({"user": me.get("username") or me.get("email") or "", "billing": billing,
                   "auth": _auth_kind(auth, billing)})
    sub = me.get("subscription") or {}
    if sub:
        credits = sub.get("credits") or {}
        status["plan"] = sub.get("plan")
        status["premium_credits"] = (credits.get("premium_credits") or {}).get("remaining")
        status["premium_resets_at"] = (credits.get("premium_credits") or {}).get("resets_at")
        status["addon_credits"] = (credits.get("add_on_credits") or {}).get("remaining")
    wallet = me.get("wallet") or {}
    if wallet:
        status["wallet_balance"] = wallet.get("remaining_balance")
        status["wallet_currency"] = wallet.get("currency")
    usage = me.get("usage_based") or {}
    if usage:
        status["usage_spent_usd"] = usage.get("spending_current_usd")
        status["usage_cap_usd"] = usage.get("spending_cap_usd")
    return status


def _version_text():
    cli = find_cli()
    if not cli:
        return ""
    try:
        return subprocess.run([cli, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def describe_auth(kind):
    return msg({"oauth": "auth_oauth", "api_key": "auth_api_key"}.get(kind, "auth_unknown"))


def print_status(status):
    if not status.get("installed"):
        print(msg("missing_cli"))
        print(msg("not_connected"))
        return
    if not status.get("connected"):
        print(msg("not_connected"))
        if status.get("env_api_key"):
            print(msg("env_key"))
        return
    print(msg("status_auth", auth=describe_auth(status.get("auth"))))
    if status.get("user"):
        print(msg("status_user", user=status["user"]))
    if status.get("plan"):
        print(msg("status_plan", plan=status["plan"]))
    if status.get("premium_credits") is not None:
        reset = f" (reset {status['premium_resets_at']})" if status.get("premium_resets_at") else ""
        print(msg("status_credits", n=status["premium_credits"], reset=reset))
    if status.get("addon_credits"):
        print(msg("status_addon", n=status["addon_credits"]))
    if status.get("wallet_balance") is not None:
        cur = "USD" if status.get("wallet_currency") in (None, "usd") else status["wallet_currency"]
        print(msg("status_wallet", bal=f"{status['wallet_balance']} {cur}"))
    if status.get("usage_spent_usd") is not None:
        print(msg("status_usage", spent=f"{status['usage_spent_usd']} USD", cap=f"{status.get('usage_cap_usd')} USD"))
    if status.get("env_api_key") and status.get("auth") != "api_key":
        print(msg("env_key"))


# ---------------------------------------------------------------- connect / disconnect

def connect(method=None, install=False):
    if not interactive():
        print(msg("need_tty"))
        return EXIT_USAGE
    print(msg("title"))
    print(msg("intro"))
    if not find_cli():
        print(msg("missing_cli"))
        if not (install or ask_yes(msg("ask_install"))):
            print(msg("install_hint"))
            return EXIT_AUTH
        print(msg("installed", path=install_cli()))
    current = account_status()
    if current.get("connected"):
        print(msg("already", desc=describe_auth(current.get("auth"))))
        if not ask_yes(msg("ask_replace")):
            print(msg("cancelled"))
            return 0
    if method is None:
        print(msg("menu"))
        try:
            choice = input(msg("ask_choice")).strip()
        except EOFError:
            choice = "3"
        if choice == "1":
            method = "remote" if is_remote() else "oauth"
        elif choice == "2":
            method = "api-key"
        else:
            print(msg("cancelled"))
            return 0
    if method in ("oauth", "remote", "device") and os.environ.get("HEYGEN_API_KEY"):
        print(msg("env_key"))
    if method == "remote":
        rc = remote_oauth()
    else:
        if method in ("oauth", "api-key"):
            print(msg("browser") if method == "oauth" else msg("key_prompt"))
        rc = run_interactive(["auth", "login", f"--{method}"])
    if rc == 130:
        return 0
    if rc != 0:
        print(msg("failed", rc=rc))
        return rc
    status = account_status()
    if not status.get("connected"):
        print(msg("failed", rc=EXIT_AUTH))
        return EXIT_AUTH
    print(msg("connected"))
    print_status(status)
    return 0


def _callback_target(pasted, redirect_uri, state):
    """Validate a pasted OAuth return address. Returns (url to call on this machine, error key or None)."""
    want = urllib.parse.urlparse(redirect_uri)
    got = urllib.parse.urlparse(pasted.strip())
    if got.scheme not in ("http", "https") or got.hostname not in ("127.0.0.1", "localhost") \
            or got.port != want.port or got.path.rstrip("/") != want.path.rstrip("/"):
        return None, "remote_bad"
    query = urllib.parse.parse_qs(got.query)
    if query.get("state", [""])[0] != state:
        return None, "remote_state"
    if "code" not in query and "error" not in query:
        return None, "remote_bad"
    return urllib.parse.urlunparse(("http", f"127.0.0.1:{want.port}", got.path, "", got.query, "")), None


class _PtyReader:
    """Accumulates what a child process writes to its pseudo-terminal."""

    def __init__(self, fd):
        self.fd = fd
        self.text = ""

    def read(self, wait):
        end = time.monotonic() + wait
        while True:
            left = end - time.monotonic()
            if left <= 0:
                return
            ready, _, _ = select.select([self.fd], [], [], left)
            if not ready:
                return
            try:
                chunk = os.read(self.fd, 4096)
            except OSError:  # the child closed its side
                return
            if not chunk:
                return
            self.text += chunk.decode("utf-8", errors="replace").replace("\r\n", "\n")

    def close(self):
        try:
            os.close(self.fd)
        except OSError:
            pass


def remote_oauth():
    """Browser OAuth for a server/SSH: the HeyGen CLI waits on a loopback port here; the person approves on any
    computer and pastes the return address, which heditor delivers to that port. The PKCE verifier never leaves
    the HeyGen CLI, so the pasted code is useless anywhere else."""
    cli = find_cli()
    if not cli:
        raise HeyGenError(msg("missing_cli") + "\n" + msg("install_hint"), EXIT_AUTH)
    # The HeyGen CLI refuses browser OAuth without a terminal, so it gets a pseudo-terminal of its own: it prints
    # the authorize URL there (BROWSER=none) and keeps its loopback server waiting for the return.
    env = dict(os.environ, BROWSER="none", HEYGEN_NO_BROWSER="1")
    master, slave = pty.openpty()
    proc = subprocess.Popen([cli, "auth", "login", "--oauth"], stdin=slave, stdout=slave, stderr=slave, env=env,
                            close_fds=True)
    os.close(slave)
    buffer = _PtyReader(master)
    url = None
    deadline = time.monotonic() + 60
    while url is None and time.monotonic() < deadline and proc.poll() is None:
        buffer.read(0.5)
        match = re.search(r"https://\S+/oauth/authorize\?\S+", buffer.text)
        if match:
            url = match.group(0)
    if url is None:
        proc.kill()
        proc.wait()
        buffer.read(0.5)
        print(buffer.text.strip())
        buffer.close()
        return proc.returncode or 1
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    redirect_uri, state = query.get("redirect_uri", [""])[0], query.get("state", [""])[0]
    prefix = redirect_uri.split("?")[0]
    print(msg("remote"))
    print()
    print(f"  {url}")
    print()
    try:
        while True:
            try:
                pasted = input(msg("remote_paste")).strip()
            except EOFError:
                pasted = ""
            if not pasted:
                print(msg("cancelled"))
                return 130
            target, problem = _callback_target(pasted, redirect_uri, state)
            if problem or target is None:
                print(msg("remote_bad", prefix=prefix) if problem != "remote_state" else msg("remote_state"))
                continue
            denied = urllib.parse.parse_qs(urllib.parse.urlparse(target).query).get("error")
            try:
                with urllib.request.urlopen(target, timeout=60) as resp:
                    resp.read()
            except urllib.error.HTTPError:
                pass  # the CLI answers the browser page; its own exit code tells whether login worked
            if denied:
                print(msg("remote_denied", error=denied[0]))
            break
        seen = len(buffer.text)
        deadline = time.monotonic() + 120
        while proc.poll() is None and time.monotonic() < deadline:
            buffer.read(0.5)
        buffer.read(0.3)
        rc = proc.returncode if proc.returncode is not None else 1
        rest = buffer.text[seen:].strip()
        if rc != 0 and rest:
            print(rest)
        return rc
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        buffer.close()


def disconnect(assume_yes=False):
    if not find_cli():
        print(msg("not_connected"))
        return 0
    if not assume_yes:
        if not interactive():
            print(msg("need_yes"))
            return EXIT_USAGE
        if not ask_yes(msg("disconnect_ask")):
            print(msg("cancelled"))
            return 0
    rc, _, err = run_cli(["auth", "logout"], timeout=60)
    if rc != 0:
        print(err.get("message") or f"heygen auth logout failed (exit {rc})")
        return rc
    print(msg("disconnected"))
    if os.environ.get("HEYGEN_API_KEY"):
        print(msg("env_key"))
    return 0


# ---------------------------------------------------------------- avatars and voices

def _paged(args, limit):
    items, token = [], None
    for _ in range(20):
        page = cli_json(args + ["--limit", str(limit)] + (["--token", token] if token else []))
        items.extend(page.get("data") or [])
        token = page.get("next_token")
        if not page.get("has_more") or not token:
            break
    return items


def list_looks():
    return _paged(["avatar", "looks", "list", "--ownership", "private"], 50)


def list_voices():
    return _paged(["voice", "list", "--type", "private"], 100)


def get_look(look_id):
    return cli_json(["avatar", "looks", "get", look_id]).get("data") or {}


def print_looks(looks):
    if not looks:
        print("no private avatar looks (create your avatar at https://app.heygen.com)")
    for look in looks:
        engines = ",".join(e.replace("avatar_", "") for e in look.get("supported_api_engines") or [])
        print(f"{look.get('id')}  {look.get('name')!r}  type={look.get('avatar_type')}  "
              f"orientation={look.get('preferred_orientation') or '?'}  engines={engines or '?'}  "
              f"status={look.get('status') or 'ready'}  default_voice={look.get('default_voice_id') or '-'}")


def print_voices(voices):
    if not voices:
        print("no cloned voices (clone yours at https://app.heygen.com or with `heygen voice clone create`)")
    for voice in voices:
        engines = ",".join(voice.get("available_engines") or [])
        print(f"{voice.get('voice_id')}  {voice.get('name')!r}  language={voice.get('language')}  "
              f"engines={engines or '?'}")


def list_glossaries():
    """Brand glossaries with their terms (term -> pronunciation respelling)."""
    items = []
    for glossary in _paged(["brand", "glossaries", "list"], 100):
        gid = glossary.get("brand_glossary_id")
        detail = cli_json(["brand", "glossaries", "get", gid]).get("data") or {} if gid else {}
        items.append({**glossary, **detail})
    return items


def print_glossaries(glossaries):
    if not glossaries:
        print("no brand glossaries (create one with `heygen brand glossaries create`; see references/heygen-avatar.md)")
    for glossary in glossaries:
        terms = glossary.get("terms") or []
        print(f"{glossary.get('brand_glossary_id')}  {glossary.get('name')!r}  terms={len(terms)}")
        for term in terms:
            print(f"    {term.get('term')}  ->  {term.get('pronunciation')}")


# ---------------------------------------------------------------- estimate

def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, timeout=60).stdout.strip()
    try:
        return float(out)
    except ValueError:
        raise HeyGenError(f"could not read the duration of {path}") from None


BREAK_TAG_RE = re.compile(r"<break\b[^>]*>", re.IGNORECASE)
BREAK_SECONDS_RE = re.compile(r'<break\s+time="(\d+(?:\.\d+)?)s"\s*/>', re.IGNORECASE)


def check_breaks(text):
    """HeyGen pause tags must be <break time="0.35s"/> (seconds); milliseconds are rejected by the API."""
    for tag in BREAK_TAG_RE.findall(text):
        if not BREAK_SECONDS_RE.fullmatch(tag):
            raise HeyGenError(f"pause tag {tag} not accepted: write it as <break time=\"0.4s\"/> (seconds, "
                              "no milliseconds)", EXIT_USAGE)


def script_seconds(text, speed=1.0):
    """Estimated spoken duration: words at WORDS_PER_SECOND / speed, plus every <break time="Ns"/> pause."""
    pauses = sum(float(s) for s in BREAK_SECONDS_RE.findall(text))
    words = len(BREAK_TAG_RE.sub(" ", text).split())
    return round(words / WORDS_PER_SECOND / (speed or 1.0) + pauses, 1)


def estimate_cost(engine, avatar_type, seconds, billing):
    """Estimated cost for `seconds` of video. Returns dict with credits or usd (None when no public rate)."""
    minutes = seconds / 60.0
    if billing == "subscription":
        rate = CREDITS_PER_MIN.get((engine, avatar_type))
        return {"unit": "credits", "rate_per_min": rate,
                "amount": None if rate is None else round(rate * minutes, 1), "rates_as_of": RATES_AS_OF}
    rate = USD_PER_MIN.get((engine, avatar_type))
    return {"unit": "usd", "rate_per_min": rate,
            "amount": None if rate is None else round(rate * minutes, 2), "rates_as_of": RATES_AS_OF}


def format_cost(cost):
    if cost["amount"] is None:
        return "no public rate for this engine/avatar type: check the HeyGen dashboard before generating"
    if cost["unit"] == "credits":
        return f"~{cost['amount']} premium credits ({cost['rate_per_min']}/min, rates {cost['rates_as_of']})"
    return f"~US$ {cost['amount']:.2f} ({cost['rate_per_min']}/min, rates {cost['rates_as_of']})"


# ---------------------------------------------------------------- avatar video

def build_request(look_id, engine, aspect, resolution, title, script=None, voice_id=None, audio_asset_id=None,
                  motion=None, glossary_id=None, speed=None):
    req = {"type": "avatar", "avatar_id": look_id, "engine": {"type": engine}, "aspect_ratio": aspect,
           "title": title, "caption": {"file_format": "srt"}}
    if resolution:
        req["resolution"] = resolution
    if script is not None:
        req["script"] = script
        if voice_id:
            req["voice_id"] = voice_id
        if glossary_id:  # pronunciation respellings: audio only, captions keep the written term
            req["brand_glossary_id"] = glossary_id
        if speed and speed != 1.0:
            req["voice_settings"] = {"speed": speed}
    else:
        req["audio_asset_id"] = audio_asset_id
    if motion:
        req["motion_prompt"] = motion
    return req


def idempotency_key(req, input_digest):
    payload = json.dumps({k: v for k, v in req.items() if k != "audio_asset_id"}, sort_keys=True) + input_digest
    return "heditor-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:40]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_video(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, timeout=60).stdout
    data = json.loads(out or "{}")
    stream = (data.get("streams") or [{}])[0]
    return {"width": stream.get("width"), "height": stream.get("height"),
            "duration": round(float((data.get("format") or {}).get("duration") or 0), 3)}


def record(work, entry):
    path = Path(work) / "avatar.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {"generations": []}
    gens = [g for g in data.get("generations", []) if g.get("video_id") != entry.get("video_id")]
    gens.append(entry)
    data["generations"] = gens
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _fetch_subtitles(url, dest):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "heditor"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        return str(dest)
    except (OSError, ValueError):
        return None


def download(work, video_id, entry=None):
    """Download a completed video into <work>/source and record it in avatar.json."""
    source = Path(work) / "source"
    source.mkdir(parents=True, exist_ok=True)
    info = cli_json(["video", "get", video_id]).get("data") or {}
    status = info.get("status")
    if status != "completed":
        if status == "failed":
            raise HeyGenError(f"video {video_id} failed: {info.get('failure_code')} {info.get('failure_message')}")
        raise HeyGenError(f"video {video_id} is {status or 'not ready'}; try again: "
                          f"heditor avatar {work} --resume {video_id}", EXIT_TIMEOUT)
    dest = source / f"avatar-{video_id}.mp4"
    cli_json(["video", "download", video_id, "--output-path", str(dest), "--force"], timeout=1800)
    if not dest.exists() or dest.stat().st_size == 0:
        raise HeyGenError(f"download of {video_id} produced no file")
    entry = dict(entry or {})
    srt = None
    if info.get("subtitle_url"):
        srt = _fetch_subtitles(info["subtitle_url"], source / f"avatar-{video_id}.srt")
    entry.update({"provider": "heygen", "video_id": video_id, "status": "downloaded", "file": str(dest),
                  "sha256": sha256_file(dest), "heygen_duration": info.get("duration"), "subtitles": srt,
                  "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "synthetic": True}, **probe_video(dest))
    entry.setdefault("disclosure", "AI-generated likeness and voice of the avatar owner (HeyGen); consent is "
                                   "verified by HeyGen when the avatar is created.")
    record(work, entry)
    return entry


def _previous_entry(work, video_id):
    try:
        data = json.loads((Path(work) / "avatar.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    for gen in data.get("generations", []):
        if gen.get("video_id") == video_id:
            return gen
    return {}


def avatar(args):
    work = Path(args.work)
    if args.resume:
        entry = download(work, args.resume, _previous_entry(work, args.resume))
        _print_done(work, entry)
        return 0
    inputs = [x for x in (args.script, args.text, args.audio) if x]
    if not args.look or len(inputs) != 1:
        raise HeyGenError("usage: heditor avatar <work> --look ID (--script FILE | --text \"...\" | --audio FILE)",
                          EXIT_USAGE)
    status = account_status()
    if not status.get("connected"):
        raise HeyGenError(msg("not_connected"), EXIT_AUTH)
    look = get_look(args.look)
    if look.get("status") not in (None, "completed"):
        raise HeyGenError(f"look {args.look} is {look.get('status')}: wait until HeyGen finishes training it")
    supported = look.get("supported_api_engines") or []
    engine = ENGINES.get((args.engine or "").lower()) if args.engine else (
        "avatar_v" if "avatar_v" in supported else "avatar_iv")
    if not engine:
        raise HeyGenError(f"unknown engine {args.engine!r}: use v, iv or iii", EXIT_USAGE)
    if supported and engine not in supported:
        raise HeyGenError(f"look {args.look} supports {', '.join(supported)}, not {engine}", EXIT_USAGE)
    script = None
    if args.script:
        script = Path(args.script).read_text(encoding="utf-8").strip()
    elif args.text:
        script = args.text.strip()
    if args.speed is not None and not 0.5 <= args.speed <= 1.5:
        raise HeyGenError("--speed must be between 0.5 and 1.5 (1.0 is the voice's natural pace)", EXIT_USAGE)
    if script is None and (args.glossary or args.speed is not None):
        raise HeyGenError("--glossary and --speed apply to synthesized speech (--script/--text); "
                          "an --audio file is lip-synced as it is", EXIT_USAGE)
    if script is not None:
        if not script:
            raise HeyGenError("the script is empty", EXIT_USAGE)
        check_breaks(script)
        seconds = script_seconds(script, args.speed or 1.0)
        digest = hashlib.sha256(script.encode("utf-8")).hexdigest()
        voice_id, voice_source = resolve_voice(args.voice, look)
        args.voice_source = voice_source
    else:
        audio = Path(args.audio)
        if not audio.exists():
            raise HeyGenError(f"audio not found: {audio}", EXIT_USAGE)
        seconds = round(probe_duration(audio), 1)
        digest = sha256_file(audio)
        voice_id = None
    if args.motion and engine == "avatar_iv" and look.get("avatar_type") != "photo_avatar":
        raise HeyGenError("--motion needs engine v for video avatars", EXIT_USAGE)
    title = args.title or f"heditor {work.name}"
    billing = status.get("billing") or ("subscription" if status.get("auth") == "oauth" else "wallet")
    cost = estimate_cost(engine, look.get("avatar_type"), seconds, billing)
    _print_plan(status, look, engine, voice_id, args, seconds, cost)
    preview = build_request(args.look, engine, args.aspect, args.resolution, title, script=script, voice_id=voice_id,
                            audio_asset_id="<uploaded audio>" if script is None else None, motion=args.motion,
                            glossary_id=args.glossary, speed=args.speed)
    if args.dry_run:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0
    if not args.yes:
        if not interactive():
            print(msg("need_yes"))
            return EXIT_USAGE
        if not ask_yes(msg("confirm")):
            print(msg("cancelled"))
            return 0
    work.mkdir(parents=True, exist_ok=True)
    asset_id = None
    if script is None:
        asset_id = (cli_json(["asset", "create", "--file", str(Path(args.audio).resolve())], timeout=600)
                    .get("data") or {}).get("asset_id")
        if not asset_id:
            raise HeyGenError("HeyGen did not return an asset_id for the audio")
    req = build_request(args.look, engine, args.aspect, args.resolution, title, script=script, voice_id=voice_id,
                        audio_asset_id=asset_id, motion=args.motion, glossary_id=args.glossary, speed=args.speed)
    key = idempotency_key(req, digest)
    rc, out, err = run_cli(["video", "create", "-d", "-", "--idempotency-key", key], stdin=json.dumps(req),
                           timeout=300)
    if rc != 0:
        text = err.get("message") or f"heygen video create failed (exit {rc})"
        raise HeyGenError(text + ("\n" + err["hint"] if err.get("hint") else ""), 1)
    video_id = ((out or {}).get("data") or {}).get("video_id")
    if not video_id:
        raise HeyGenError("HeyGen did not return a video_id")
    entry = {"provider": "heygen", "video_id": video_id, "status": "rendering", "look_id": args.look,
             "look_name": look.get("name"), "avatar_type": look.get("avatar_type"), "engine": engine,
             "voice_id": voice_id, "glossary_id": args.glossary, "speed": args.speed,
             "input": "script" if script is not None else "audio",
             "input_sha256": digest, "audio_file": str(Path(args.audio).resolve()) if args.audio else None,
             "aspect_ratio": args.aspect, "resolution": args.resolution, "billing": billing,
             "auth": status.get("auth"), "estimate_seconds": seconds, "estimated_cost": cost,
             "requested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "synthetic": True}
    if script is not None:
        (work / "source").mkdir(parents=True, exist_ok=True)
        script_file = work / "source" / f"avatar-{video_id}.txt"
        script_file.write_text(script + "\n", encoding="utf-8")
        entry["script_file"] = str(script_file)
    record(work, entry)
    print(f"video {video_id} requested; waiting for HeyGen to render (timeout {args.timeout})")
    if _wait(video_id, args.timeout) == EXIT_TIMEOUT:
        print(f"still rendering. Resume later with: heditor avatar {work} --resume {video_id}")
        return EXIT_TIMEOUT
    entry = download(work, video_id, entry)
    _print_done(work, entry)
    return 0


def _wait(video_id, timeout):
    """Poll `heygen video get` with backoff until the video completes, fails or the timeout passes."""
    seconds = _parse_timeout(timeout)
    deadline = time.monotonic() + seconds
    delay = 5.0
    while True:
        info = cli_json(["video", "get", video_id], timeout=60).get("data") or {}
        status = info.get("status")
        if status == "completed":
            return 0
        if status == "failed":
            raise HeyGenError(f"video {video_id} failed: {info.get('failure_code')} {info.get('failure_message')}")
        if time.monotonic() + delay > deadline:
            return EXIT_TIMEOUT
        time.sleep(delay)
        delay = min(delay * 1.5, 30.0)


def _parse_timeout(text):
    text = str(text).strip().lower()
    units = {"s": 1, "m": 60, "h": 3600}
    if text and text[-1] in units:
        return float(text[:-1]) * units[text[-1]]
    return float(text)


def _print_plan(status, look, engine, voice_id, args, seconds, cost):
    print(f"account:  {status.get('user') or '?'}  ({describe_auth(status.get('auth'))})")
    if status.get("premium_credits") is not None:
        print(f"credits:  {status['premium_credits']} premium credits left")
    if status.get("wallet_balance") is not None:
        print(f"balance:  {status['wallet_balance']} {status.get('wallet_currency') or 'usd'}")
    print(f"look:     {look.get('id') or args.look}  {look.get('name')!r}  type={look.get('avatar_type')}  "
          f"orientation={look.get('preferred_orientation') or '?'}")
    print(f"engine:   {engine}   aspect: {args.aspect}   resolution: {args.resolution or 'default'}")
    if voice_id:
        print(f"voice:    {voice_id}  ({getattr(args, 'voice_source', '--voice')})"
              + (f"   speed: {args.speed}" if args.speed is not None else ""))
    if args.script or args.text:
        print(f"glossary: {args.glossary}" if args.glossary else
              "glossary: none (terms are read as written; see heditor heygen glossaries)")
    source = "script" if (args.script or args.text) else f"audio {args.audio}"
    print(f"input:    {source}, ~{seconds:.1f} s")
    print(f"estimate: {format_cost(cost)}; HeyGen bills the real duration")
    if args.aspect == "9:16" and look.get("preferred_orientation") == "landscape":
        print("warning:  this look was recorded in landscape; a 9:16 output crops or letterboxes it")


def _print_done(work, entry):
    print(f"saved:    {entry['file']}  ({entry.get('width')}x{entry.get('height')}, {entry.get('duration')} s)")
    if entry.get("subtitles"):
        print(f"captions: {entry['subtitles']} (HeyGen sidecar; heditor words still re-times every word)")
    print(f"record:   {Path(work) / 'avatar.json'}")
    print(f"next:     heditor new {work} {entry['file']}   then the normal workflow (prepare, words, DESIGN.md...)")
    print("remember: synthetic video of a real person: say only what the person approved, and disclose AI use "
          "where the platform or the law asks for it")


# ---------------------------------------------------------------- CLI

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "avatar":
        parser = argparse.ArgumentParser(prog="heditor avatar")
        parser.add_argument("work")
        parser.add_argument("--look", help="avatar look id (heditor heygen avatars)")
        parser.add_argument("--script", help="text file with the script")
        parser.add_argument("--text", help="the script inline")
        parser.add_argument("--audio", help="audio file to lip-sync (mp3/wav), e.g. your own recording")
        parser.add_argument("--voice", help="voice id for a script (default: brand.json heygen.voice_id, else the "
                                            "look's default voice if it is one of your cloned voices)")
        parser.add_argument("--engine", help="v, iv or iii (default: v when the look supports it)")
        parser.add_argument("--aspect", default="9:16", choices=["9:16", "16:9", "4:5", "5:4", "1:1", "auto"])
        parser.add_argument("--resolution", default="1080p", choices=["720p", "1080p", "4k"])
        parser.add_argument("--motion", help="motion prompt (engine v for video avatars)")
        parser.add_argument("--glossary", metavar="ID",
                            help="brand glossary id: pronunciation respellings for the synthesized speech "
                                 "(heditor heygen glossaries); captions keep the written terms")
        parser.add_argument("--speed", type=float, help="voice speed 0.5-1.5 (default: the voice's natural pace)")
        parser.add_argument("--title")
        parser.add_argument("--timeout", default="30m")
        parser.add_argument("--dry-run", action="store_true", help="show plan, estimate and request; spend nothing")
        parser.add_argument("--yes", action="store_true",
                            help="skip the confirmation (only after the cost is approved)")
        parser.add_argument("--resume", metavar="VIDEO_ID", help="download a video that was still rendering")
        return avatar(parser.parse_args(argv[1:]))
    parser = argparse.ArgumentParser(prog="heditor heygen", description="optional HeyGen connection")
    sub = parser.add_subparsers(dest="cmd", required=True)
    con = sub.add_parser("connect")
    group = con.add_mutually_exclusive_group()
    group.add_argument("--oauth", dest="method", action="store_const", const="oauth")
    group.add_argument("--remote", dest="method", action="store_const", const="remote",
                       help="HeyGen account from a server/SSH: open the link elsewhere and paste the return address")
    group.add_argument("--device", dest="method", action="store_const", const="device",
                       help="HeyGen device-code login (depends on HeyGen enabling it for the CLI)")
    group.add_argument("--api-key", dest="method", action="store_const", const="api-key")
    con.add_argument("--install", action="store_true", help="install the HeyGen CLI without asking")
    st = sub.add_parser("status")
    st.add_argument("--json", action="store_true")
    dis = sub.add_parser("disconnect")
    dis.add_argument("--yes", action="store_true")
    for name in ("avatars", "voices", "glossaries"):
        sub.add_parser(name).add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "connect":
        return connect(args.method, args.install)
    if args.cmd == "status":
        status = account_status()
        if args.json:
            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            print_status(status)
        return 0 if status.get("connected") else EXIT_AUTH
    if args.cmd == "disconnect":
        return disconnect(args.yes)
    if args.cmd == "glossaries":
        items = list_glossaries()
        if args.json:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            print_glossaries(items)
        return 0
    items = list_looks() if args.cmd == "avatars" else list_voices()
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    elif args.cmd == "avatars":
        print_looks(items)
    else:
        print_voices(items)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except HeyGenError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(exc.code)
    except KeyboardInterrupt:
        print(msg("cancelled"), file=sys.stderr)
        sys.exit(130)
