"""Style `lapidacao`: the speech as a luxury jewellery commercial. Runs as-is once beats.json and the object photos
exist; make it yours by rewriting beats.json from the speech (format below) and, if needed, the scenes.

The raw idea is a rough stone, refining it is the cut, the result is the cut gem (with its facets named by the speech),
the machine comes in only after that, a jeweller's loupe reviews its work, a display tray shows the steps (the unsaid
ones locked), a certificate grades the result, the offer is a jewellery case that opens and slams shut on the warning,
the condition is a sealed tag with the date, the access is a velvet rope and the CTA button opens it. The speaker is
cut out (matte) in a black void under a cool spotlight; the room shows only in the hook and goes dark on a declared
pause. Recipe and rules: references/styles/lapidacao.md.

    heditor new <work> <video> --style lapidacao       # scaffolds this file, prepare.py and DESIGN.md
    # prepare.py: BLOCKS with ("PAUSE", 0.5, "p_apagao") right after the hook block; heditor prepare; heditor words
    # generate the five object photos into <work>/gen/ (prompts: lapidacao_kit.OBJECT_PROMPTS; no text, no logos)
    # write <work>/beats.json (format below; start from templates/styles/lapidacao/beats.example.json), then:
    heditor produce <work> lapidacao 0                 # music: beats.json "music" or the style default

beats.json = {"keys": {...}, "text": {...}, "floor": [[key, text], ...], "allowed_numbers": [...], "music": {...}}
  keys   every event below -> [spoken token, after_seconds] (token without punctuation, accents must match; "after"
         disambiguates repeats). Hook: tab (tab name types in), freeze (editor stops), cursor (cursor leaves), close
         (click on the red dot; the window implodes). Spotlight: spot_punch. Plaques: plaque1, plaque2, plaque_sheen,
         glyph1, cut1, glyph2, cut2. Raw step: step1, sheet, caret, line1..line5, lines_end, compact, land.
         The cut: step2, riser, laser, shards, flash, title, subtitle, doc, row2, row3, row4, rows_dim (row 1 lights
         on doc). Machine: machine, machine_on, pill, tasks, code, loupe, stamp. Tray: tray, tray_in, tray_title,
         niches, tray_sheen. Certificate: cert, cert1, cert2, cert3, cert_seal. Case: case, case_open, case_gem,
         case_glow, case_seal, forever, flicker, slam. Condition: tag, flip, tag_time, tag_note, rope, vip_plate,
         vip_sheen. CTA: cta, button, rope_open, bell, toggle, envelope, envelope_seal, fin, fin_line, final_punch.
  text   on-screen words, exactly as spoken (see TEXT_DEFAULTS for every field)
  floor  big engraved word on the velvet floor (atmosphere under the ad UI), one per act: [[key, "WORD"], ...]
  music  {"main": "music:126" | "m<mixkit id>" | path, "drop": 48.0, "cta": "m179" | path, "cta_src": 28.0}
Every number on screen must be spoken (or listed in allowed_numbers with the reason in DESIGN.md).
"""
import html
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("HEDITOR_KIT", str(Path.home() / ".heditor/kit")))
import lapidacao_kit as lk  # noqa: E402
import reelkit as rk  # noqa: E402

WORK = Path(__file__).resolve().parent
CTA = 4.3
SEED = 20261021
SPOT_X = {"full": 540, "right": 740, "left": 340, "low": 540}   # face centre x of each rig state
EVENTS = ("tab freeze cursor close spot_punch plaque1 plaque2 plaque_sheen glyph1 cut1 glyph2 cut2 step1 sheet caret "
          "line1 line2 line3 line4 line5 lines_end compact land step2 riser laser shards flash title subtitle doc row2 "
          "row3 row4 rows_dim machine machine_on pill tasks code loupe stamp tray tray_in tray_title niches tray_sheen "
          "cert cert1 cert2 cert3 cert_seal case case_open case_gem case_glow case_seal forever flicker slam tag flip "
          "tag_time tag_note rope vip_plate vip_sheen cta button rope_open bell toggle envelope envelope_seal fin "
          "fin_line final_punch").split()
TEXT_DEFAULTS = {
    "hook": ["A PRIMEIRA COISA", "QUE EU FAÇO"], "hook_window": "editor de código", "hook_tab": "sistema-novo",
    "code": [["<b>def</b> <em>cadastrar_cliente</em>(dados):", 0], ["<s># regra: e-mail único</s>", 1],
             ["<b>if</b> Cliente.existe(dados.email):", 1], ['<b>raise</b> <em>Erro</em>(<u>"e-mail já existe"</u>)', 2],
             ["cliente = Cliente(**dados)", 1], ["cliente.salvar()", 1], ["<b>return</b> cliente", 1], ["", 0],
             ["<b>def</b> <em>listar_clientes</em>(filtro):", 0], ["<b>return</b> Cliente.buscar(filtro)", 1]],
    "floor0": "EDITOR",
    "plaques": [{"label": "PASSO", "n": "01", "glyph": "code-xml", "sub": "SEM CÓDIGO"},
                {"label": "PASSO", "n": "02", "glyph": "settings", "sub": "SEM ETAPA TÉCNICA"}],
    "step1": "PASSO 01", "step2": "PASSO 02",
    "sheet_window": "editor de texto",
    "sheet_lines": ["tudo sobre o sistema,", "tudo sobre a ideia,", "levantamentos,", "requisitos,", "especificações…"],
    "raw_label": "PROMPT BRUTO", "gem_title": "PRD", "gem_sub": ["PRODUCT REQUIREMENT", "DOCUMENT"],
    "rows": ["REQUISITOS", "ESPECIFICAÇÕES", "DETALHES TÉCNICOS", "IMPLEMENTAÇÃO"],
    "machine_window": "editor de código", "pill": "IA", "badge": "PRD",
    "tasks": ["REQUISITOS", "DETALHES TÉCNICOS", "IMPLEMENTAÇÃO"], "stamp": "REVISADO",
    "tray_title": "WORKFLOW DE IA",
    "niches": [{"img": "stone", "label": "PROMPT BRUTO"}, {"img": "diamond", "label": "PRD"}, {"lock": True},
               {"lock": True}, {"lock": True}],
    "cert_title": "CERTIFICADO", "cert_rows": ["PROFISSIONAL", "ESCALÁVEL", "STACK DE PONTA"],
    "case_seal": ["BLACK NOVEMBER", ""], "forever": "ACESSO VITALÍCIO",
    "tag_front": "CONDIÇÃO", "tag_date": "05/11", "tag_time": "19H30", "tag_note": "AULA ESPECIAL",
    "vip": "GRUPO VIP", "button": "SAIBA MAIS", "bell": "NOTIFICAÇÕES",
    "envelope": ["MAIS INFORMAÇÕES", "NO GRUPO VIP"], "fin": ["05/11 · 19H30", "LINK DA AULA NO GRUPO VIP"],
    "end_title": "BLACK NOVEMBER", "end_sub": "DA {brand} · 05/11", "end_line": "Clique em Saiba Mais e entre no grupo VIP",
    "seal_final": ["Black November da {brand}", "05/11"],
}


def load_beats():
    p = WORK / "beats.json"
    if not p.exists():
        raise SystemExit(f"lapidacao: write {p} from the speech first (format at the top of build.py)")
    b = json.loads(p.read_text())
    missing = [e for e in EVENTS if e not in b.get("keys", {})]
    if missing:
        raise SystemExit(f"lapidacao: beats.json keys missing: {missing}")
    brand = rk.load_brand(WORK)
    t = dict(TEXT_DEFAULTS)
    t.update(b.get("text", {}))
    for f in ("end_sub",):
        t[f] = t[f].replace("{brand}", brand["name"].upper())
    t["seal_final"] = [x.replace("{brand}", brand["name"]) for x in t["seal_final"]]
    if not t["case_seal"][1]:
        t["case_seal"] = [t["case_seal"][0], brand["name"].upper()]
    t["brand"] = brand["name"].upper()
    return b, t


# ------------------------------------------------------------------ words, keys
def load():
    f = WORK / "words-reviewed.json" if (WORK / "words-reviewed.json").exists() else WORK / "words.json"
    words = rk.load_words(f)
    edl = json.loads((WORK / "edl.json").read_text())
    return words, round(edl["voice_duration"], 3), edl


def keys(words, voice_end, beats):
    find = rk.finder(words)
    k = {}
    for key in EVENTS:
        tok, after = beats["keys"][key]
        k[key] = find(rk.plain(tok), float(after))
    k["voice_end"] = voice_end
    k["duration"] = round(voice_end + CTA, 3)
    return k


# ------------------------------------------------------------------ captions (world-native, one line)
def caption_html(caps):
    out = []
    for c in caps:
        n = len(c["text"])
        fs = int(min(78, 800 / (0.66 * max(n, 6))))
        words = " ".join(f'<span id="{c["id"]}-w{j}" class="w">{html.escape(w["shown"])}</span>'
                         for j, w in enumerate(c["words"]))
        out.append(f'<div id="{c["id"]}" class="clip caption" data-start="{c["start"]:.4f}" '
                   f'data-duration="{c["end"] - c["start"]:.4f}" data-track-index="50">'
                   f'<div id="{c["id"]}-c" class="cap" style="font-size:{fs}px">{words}</div></div>')
    return "".join(out)


def typed(text, cls="ch"):
    return "".join(f'<span class="{cls}">{"&nbsp;" if ch == " " else html.escape(ch)}</span>' for ch in text)


# ------------------------------------------------------------------ page
def scenes(T):
    E = html.escape
    glyphs = [p.get("glyph", "code-xml") for p in T["plaques"]]
    ic = {n: rk.icon(n) for n in {"code-xml", "mouse-pointer-2", "lock", "bell", "check", "settings", "chevron-down",
                                  "pointer", *glyphs}}
    ghost = "".join(f'<i class="gl" style="width:{w}%"></i>' for w in (62, 80, 45, 70, 88, 52, 66, 40, 74))
    fill = "".join(f'<i class="fl" style="width:{w}%"></i>' for w in (92, 84, 96, 70, 88, 94, 60, 90, 78, 86, 72, 95))
    code = "".join(f'<div class="cl" style="padding-left:{18 + 26 * ind}px">{ln or "&nbsp;"}</div>' for ln, ind in T["code"])
    ticks = "".join(f'<div class="ck" id="ck{i}">{ic["check"]}</div>' for i in range(7))
    dust = "".join('<i class="d"></i>' for _ in range(46))
    sparks = "".join('<i class="spk"></i>' for _ in range(16))
    shards = "".join('<i class="shd"></i>' for _ in range(10))
    stars = "".join('<i class="star"></i>' for _ in range(7))
    facets = ("M 70 205 L 205 70 L 340 205 L 205 340 Z M 70 205 L 340 205 M 205 70 L 205 340 "
              "M 120 150 L 290 260 M 290 150 L 120 260 M 135 120 L 275 120 M 135 290 L 275 290")
    niches = []
    for i, n in enumerate(T["niches"][:5]):
        if n.get("img") in ("stone", "diamond"):
            src = "obj-stone-raw.png" if n["img"] == "stone" else "obj-diamond.png"
            inner, lab = f'<img class="nimg" src="assets/{src}">', E(n.get("label", ""))
        else:
            inner, lab = f'<div class="ncov">{ic["lock"]}<span>?</span></div>', "&nbsp;"
        niches.append(f'<div class="ni" id="ni{i}"><div class="nn">0{i + 1}</div>{inner}<div class="nl">{lab}</div></div>')
    plq = []
    for i, p in enumerate(T["plaques"][:2]):
        g = ic[p.get("glyph", "code-xml")]
        plq.append(f'<div class="plq" id="pl{i + 1}"><div class="pk">{E(p["label"])}</div><div class="pn">{E(p["n"])}</div>'
                   f'<div class="glyph" id="{"gcode" if i == 0 else "ggear"}"><div class="gh a">{g}</div><div class="gh b">{g}</div>'
                   f'<i class="slash"></i></div><div class="ps">{E(p["sub"])}</div></div>')
    lines = "".join(f'<div class="sl" id="sl{i + 1}">{typed(t)}</div>' for i, t in enumerate(T["sheet_lines"][:5]))
    rows = "".join(f'<div class="row" id="r{i + 1}"><i class="rc">{ic["check"]}</i><span>{E(r)}</span></div>'
                   for i, r in enumerate(T["rows"][:4]))
    tasks = "".join(f'<div class="tk" id="tk{i + 1}"><i class="tb">{ic["check"]}</i>{E(t)}</div>' for i, t in enumerate(T["tasks"][:3]))
    chips = "".join(f'<div class="chip" id="cp{i + 1}">{E(t)}</div>' for i, t in enumerate(T["tasks"][:3]))
    cert = "".join(f'<div class="ct-r" id="c{i + 1}"><span>{E(r)}</span><i>{ic["check"]}</i></div>' for i, r in enumerate(T["cert_rows"][:3]))
    return f"""
<div id="void"><div id="floor"></div>
  <div id="spot"><div id="cone"></div><div id="halo"></div><div id="pool"></div><div id="dust">{dust}</div></div>
</div>
<div id="mark">{E(T["brand"])}</div>
<div id="hook"><div class="h1">{E(T["hook"][0])}</div><div class="h2">{E(T["hook"][1])}<b>…</b></div></div>
<div id="floorword"><span id="fw">{E(T["floor0"])}</span></div>

<!-- hook: the code editor that gets closed -->
<div class="persp" id="edw"><div class="win" id="ed">
  <div class="bar"><i class="dot r" id="edx"></i><i class="dot y"></i><i class="dot g"></i><span class="wt">{E(T["hook_window"])}</span></div>
  <div class="tabs"><span class="tab"><span id="edtab">{typed(T["hook_tab"])}</span></span></div>
  <div class="ebody"><div class="ghost">{ghost}</div>
    <div class="splash">{ic["code-xml"]}<div class="pbar"><div id="edprog"></div></div></div>
    <div id="edcode">{code}</div>
  </div>
</div></div>
<div id="cur">{ic["mouse-pointer-2"]}</div>
<div id="crt"></div>

<!-- two plaques -->
{"".join(plq)}

<div id="hdr"><span id="hdr-t">{E(T["step1"])}</span><i></i></div><div id="ospot"></div>

<!-- raw step: plain text editor sheet -->
<div class="persp" id="shw"><div id="sheet">
  <div class="sbar"><i class="sd"></i><i class="sd"></i><i class="sd"></i><span>{E(T["sheet_window"])}</span></div>
  <div class="sbody">{lines}<div class="fill">{fill}</div><i id="caret"></i></div>
</div></div>

<!-- the stone and the cut -->
<div id="gem">
  <div id="ped"></div>
  <img id="stone" src="assets/obj-stone-raw.png">
  <img id="dia" src="assets/obj-diamond.png">
  <svg id="fac" viewBox="0 0 410 410"><path d="{facets}"/></svg>
  <i id="laser"></i>
  <div id="sparks">{sparks}</div><div id="shards">{shards}</div><div id="stars">{stars}</div>
</div>
<div class="eng big" id="lb-bruto">{E(T["raw_label"])}</div>
<div class="eng huge" id="lb-prd">{E(T["gem_title"])}</div>
<div class="eng sub" id="lb-prd2">{"<br>".join(E(x) for x in T["gem_sub"])}</div>
<div id="rows">{rows}</div>

<!-- the machine comes in only now -->
<div id="badge"><img src="assets/obj-diamond.png"><span>{E(T["badge"])}</span><i class="bline"></i></div>
<div id="ed2" class="win dark2">
  <div class="bar"><i class="dot r"></i><i class="dot y"></i><i class="dot g"></i><span class="wt">{E(T["machine_window"])}</span>
    <span id="iapill"><i></i>{E(T["pill"])}</span></div>
  <div id="tasks">{tasks}</div>
  <div id="codebox"><div id="code">{code}</div><div id="ticks">{ticks}</div></div>
  <div id="revis">{E(T["stamp"])}</div>
</div>
<div id="loupe"><div id="lz"><div id="lzc">{code}</div></div><i id="lring"></i><i id="lhandle"></i></div>
{chips}

<!-- display tray -->
<div class="eng mid" id="wtitle">{E(T["tray_title"])}</div>
<div id="tray">{"".join(niches)}<i id="traysheen"></i></div>

<!-- certificate -->
<div id="cert">
  <div class="ct-k">{E(T["cert_title"])}</div><div class="ct-line"></div>{cert}
  <div id="cseal"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="54"/><circle cx="60" cy="60" r="44"/>
    <path d="M60 30 L67 52 L90 52 L71 66 L78 88 L60 74 L42 88 L49 66 L30 52 L53 52 Z"/></svg></div>
</div>

<!-- the case -->
<div id="case">
  <img id="boxo" src="assets/obj-box-open.png"><img id="boxc" src="assets/obj-box-closed.png">
  <img id="minidia" src="assets/obj-diamond.png">
  <div id="rib"><i class="rv"></i><i class="rh"></i><i class="bow">{ic["lock"]}</i></div>
</div>
<div id="seal"><div class="s1">{E(T["case_seal"][0])}</div><div class="s2">{E(T["case_seal"][1])}</div></div>
<div id="vital"><svg viewBox="0 0 120 60"><path id="inf" d="M60 30 C 45 8, 12 8, 12 30 C 12 52, 45 52, 60 30 C 75 8, 108 8, 108 30 C 108 52, 75 52, 60 30 Z"/></svg><span>{E(T["forever"])}</span></div>
<div class="persp" id="tagw"><div id="tag"><i id="tstring"></i>
  <div class="tf front">{ic["lock"]}<span>{E(T["tag_front"])}</span></div>
  <div class="tf back"><div class="t1">{E(T["tag_date"])}</div><div class="t2" id="t2">{E(T["tag_time"])}</div><div class="t3" id="t3">{E(T["tag_note"])}</div></div>
</div></div>
<div id="rope"><img class="rp" id="ropeL" src="assets/obj-rope.png"><img class="rp" id="ropeR" src="assets/obj-rope.png">
  <div id="vip">{E(T["vip"])}</div></div>

<!-- CTA -->
<div id="btn"><span>{E(T["button"])}</span><b>›</b></div><div id="tap"></div><div id="finger">{ic["pointer"]}</div>
<div id="chev">{ic["chevron-down"]}{ic["chevron-down"]}</div>
<div id="bellrow"><div id="bicon">{ic["bell"]}</div><span>{E(T["bell"])}</span><div id="tog"><i></i></div></div>
<div id="env"><div class="flap"></div><div class="wax">{E(T["brand"][:1])}</div><span>{"<br>".join(E(x) for x in T["envelope"])}</span></div>
<div id="fin"><div class="f1">{E(T["fin"][0])}</div><div class="f2">{E(T["fin"][1])}</div></div>

<!-- end card -->
<div id="endt"><div class="e1">{E(T["end_title"])}</div><div class="e2">{E(T["end_sub"])}</div></div>
<div id="endl">{E(T["end_line"])}</div>
<div id="sealfinal"><div class="sf1">{E(T["seal_final"][0])}</div><div class="sf2">{E(T["seal_final"][1])}</div></div>
"""


CSS = r"""
@font-face{font-family:Geist;src:url('assets/Geist-VF.ttf');font-weight:100 900;font-display:block}
@font-face{font-family:JBM;src:url('assets/JetBrainsMono-VF.ttf');font-weight:100 900;font-display:block}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden;background:#000;font-family:Geist,sans-serif;color:#eef3f7}
#stage{position:relative;width:1080px;height:1920px;overflow:hidden;background:#050506}
.clip{position:absolute}
.ic{width:48px;height:48px;stroke-width:2;flex:none}
#void{position:absolute;inset:0;background:radial-gradient(ellipse 120% 70% at 50% 30%,#0b0c10 0%,#050506 55%,#020203 100%);z-index:0}
#floor{position:absolute;left:0;top:1000px;width:1080px;height:920px;background:
  radial-gradient(ellipse 60% 30% at 50% 30%,rgba(150,160,180,.07),rgba(0,0,0,0) 70%),linear-gradient(180deg,rgba(7,7,10,0),#060609 25%,#020203)}
#spot{position:absolute;inset:0;z-index:1}
#cone{position:absolute;left:190px;top:-80px;width:700px;height:1400px;opacity:0;
  background:radial-gradient(ellipse 50% 100% at 50% 0%,rgba(220,232,255,.20),rgba(220,232,255,.05) 55%,rgba(220,232,255,0) 75%);
  clip-path:polygon(43% 0,57% 0,100% 100%,0 100%);filter:blur(6px)}
#halo{position:absolute;left:190px;top:240px;width:700px;height:900px;opacity:0;
  background:radial-gradient(ellipse 50% 50% at 50% 45%,rgba(190,205,230,.22),rgba(190,205,230,0) 70%)}
#dust{position:absolute;left:240px;top:0;width:600px;height:1200px;opacity:0}
#dust .d{position:absolute;width:4px;height:4px;border-radius:50%;background:rgba(235,240,255,.55)}
#mark{position:absolute;left:84px;top:1180px;width:912px;text-align:center;font-weight:700;font-size:26px;letter-spacing:.5em;color:#EDC580;opacity:.9;z-index:20}

#prig{position:absolute;left:0;top:0;width:1080px;height:1920px;transform-origin:0 0;z-index:5}
#pj,#pp{position:absolute;inset:0;transform-origin:48% 59%}
#plate{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover;
  -webkit-mask-image:radial-gradient(ellipse 62% 52% at 48% 52%,#000 55%,rgba(0,0,0,0) 100%);
  -webkit-mask-repeat:no-repeat;-webkit-mask-size:100% 100%}
#platew{position:absolute;left:0;top:0;width:1080px;height:1920px}
#pbox{position:absolute;left:0;top:0;width:1080px;height:2040px;
  -webkit-mask-image:linear-gradient(180deg,#000 74%,rgba(0,0,0,0) 93%),linear-gradient(90deg,rgba(0,0,0,0) 0,#000 10%,#000 90%,rgba(0,0,0,0) 100%);
  -webkit-mask-composite:source-in;mask-composite:intersect;-webkit-mask-repeat:no-repeat;-webkit-mask-size:100% 100%}
#alpha{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover}
#rim{position:absolute;left:250px;top:520px;width:580px;height:760px;border-radius:50%;
  background:radial-gradient(ellipse 50% 50% at 50% 50%,rgba(210,222,245,.16),rgba(210,222,245,0) 70%);opacity:0}

.persp{position:absolute;perspective:1300px;z-index:8}
.win{position:absolute;inset:0;border-radius:20px;overflow:hidden;background:#0d1016;
  box-shadow:0 40px 90px rgba(0,0,0,.7),0 0 0 1px rgba(255,255,255,.08)}
.bar{height:56px;display:flex;align-items:center;gap:12px;padding:0 20px;background:#151922;border-bottom:1px solid rgba(255,255,255,.06)}
.dot{width:16px;height:16px;border-radius:50%;display:inline-block}.dot.r{background:#ff5f57}.dot.y{background:#febc2e}.dot.g{background:#28c840}
.wt{margin-left:12px;font-size:22px;color:#9aa3b2;font-weight:500}
.tabs{height:48px;background:#11141b;display:flex;align-items:flex-end;padding-left:14px}
.tab{height:40px;padding:0 18px;display:flex;align-items:center;background:#0d1016;border-radius:10px 10px 0 0;font-family:JBM;font-size:20px;color:#d7dde6}
.ch{opacity:0}
.ebody{position:absolute;left:0;right:0;top:104px;bottom:0}
.ghost{position:absolute;left:28px;right:28px;top:26px;display:flex;flex-direction:column;gap:20px;opacity:.5}
.gl{display:block;height:14px;border-radius:7px;background:#1d2330}
.splash{position:absolute;left:0;right:0;top:130px;display:flex;flex-direction:column;align-items:center;gap:22px}
.splash .ic{width:120px;height:120px;color:#7fb1ff;stroke-width:1.5}
.sp-t{font-size:30px;color:#c9d2de;font-weight:500}
.pbar{width:340px;height:12px;border-radius:6px;background:#1d2330;overflow:hidden}
#edprog{width:100%;height:100%;background:linear-gradient(90deg,#6aa3ff,#bcd6ff);transform-origin:0 50%}
#edw{left:74px;top:522px;width:476px;height:500px}
#hook{position:absolute;left:84px;top:330px;width:480px;z-index:20;font-weight:800;line-height:1.04;letter-spacing:.01em}
#hook .h1{font-size:58px;color:#fff;text-shadow:0 6px 20px rgba(0,0,0,.8)}
#hook .h2{font-size:58px;color:#EDC580;text-shadow:0 6px 20px rgba(0,0,0,.8)}
#hook b{color:#fff}
#edcode{position:absolute;left:0;right:0;top:14px;font-family:JBM;font-size:18px;line-height:30px;color:#e7ecf3;white-space:nowrap}
#edcode .cl{opacity:0;height:30px}
#floorword{position:absolute;left:0;top:1262px;width:1080px;height:260px;z-index:2;text-align:center;opacity:0}
#fw{display:inline-block;font-weight:800;letter-spacing:.04em;white-space:nowrap;line-height:1;
  background:linear-gradient(180deg,rgba(237,197,128,.30),rgba(237,197,128,.04));-webkit-background-clip:text;background-clip:text;color:transparent}
#pool{position:absolute;left:190px;top:1130px;width:700px;height:240px;border-radius:50%;opacity:0;
  background:radial-gradient(ellipse 50% 50% at 50% 50%,rgba(205,215,235,.16),rgba(205,215,235,0) 70%)}
#ospot{position:absolute;left:30px;top:300px;width:580px;height:760px;z-index:7;opacity:0;
  background:radial-gradient(ellipse 50% 50% at 50% 42%,rgba(215,225,245,.14),rgba(215,225,245,0) 68%)}
#ed{transform-origin:0% 50%}
#cur{position:absolute;left:470px;top:920px;width:64px;height:64px;z-index:12;color:#fff;filter:drop-shadow(0 6px 10px rgba(0,0,0,.7))}
#cur .ic{width:64px;height:64px;fill:#fff;stroke:#111;stroke-width:1.2}
#crt{position:absolute;left:74px;top:770px;width:476px;height:6px;background:#dce8ff;box-shadow:0 0 30px 8px rgba(190,215,255,.7);opacity:0;z-index:9;border-radius:3px}

.plq{position:absolute;top:318px;width:212px;height:420px;border-radius:16px;z-index:8;text-align:center;
  background:linear-gradient(180deg,#121318,#08080b);border:1px solid rgba(237,197,128,.55);
  box-shadow:0 30px 60px rgba(0,0,0,.6),inset 0 1px 0 rgba(255,255,255,.08)}
#pl1{left:80px}#pl2{left:788px}
.pk{margin-top:22px;font-size:22px;letter-spacing:.42em;color:#EDC580;font-weight:600}
.pn{font-size:84px;font-weight:250;color:#f3f5f8;line-height:1;margin-top:4px}
.ps{position:absolute;left:0;right:0;bottom:20px;font-size:22px;letter-spacing:.14em;color:#EDC580;font-weight:700;opacity:0;line-height:1.3;padding:0 14px}
.glyph{position:absolute;left:16px;top:150px;width:180px;height:180px;opacity:0}
.gh{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
.gh .ic{width:150px;height:150px;color:#dfe6f0;stroke-width:1.4}
.gh.a{clip-path:polygon(0 0,100% 0,100% 38%,0 62%)}.gh.b{clip-path:polygon(0 62%,100% 38%,100% 100%,0 100%)}
.slash{position:absolute;left:-10px;top:88px;width:200px;height:5px;background:#fff;box-shadow:0 0 18px 6px rgba(237,197,128,.8);
  transform:rotate(-12deg) scaleX(0);transform-origin:0 50%;border-radius:3px}

#hdr{position:absolute;left:84px;top:306px;z-index:20;display:flex;align-items:center;gap:18px;opacity:0}
#hdr-t{font-size:26px;letter-spacing:.42em;color:#EDC580;font-weight:600}
#hdr i{display:block;width:120px;height:2px;background:linear-gradient(90deg,#EDC580,rgba(237,197,128,0))}

#shw{left:84px;top:392px;width:472px;height:560px}
#sheet{position:absolute;inset:0;border-radius:16px;overflow:hidden;background:#f2f4f7;
  transform-origin:0 50%;box-shadow:0 40px 90px rgba(0,0,0,.65)}
.sbar{height:46px;display:flex;align-items:center;gap:10px;padding:0 18px;background:#e3e7ed}
.sd{width:13px;height:13px;border-radius:50%;background:#c3c9d2}
.sbar span{margin-left:8px;font-size:20px;color:#5d6673;font-weight:500}
.sbody{position:absolute;left:26px;right:22px;top:66px;bottom:16px}
.sl{font-size:33px;line-height:1.28;color:#14171c;font-weight:500;white-space:nowrap}
.fill{display:flex;flex-direction:column;gap:12px;margin-top:16px}
.fl{display:block;height:11px;border-radius:6px;background:#c9cfd8;opacity:0}
#caret{position:absolute;width:3px;height:38px;background:#14171c;left:0;top:0;opacity:0}

#gem{position:absolute;left:110px;top:392px;width:410px;height:410px;z-index:8}
#gem img{position:absolute;left:0;top:0;width:410px;height:410px}
#ped{position:absolute;left:-30px;top:350px;width:470px;height:90px;border-radius:50%;opacity:0;
  background:radial-gradient(ellipse 50% 50% at 50% 50%,rgba(200,210,230,.20),rgba(0,0,0,0) 70%)}
#fac{position:absolute;left:0;top:0;width:410px;height:410px;overflow:visible;opacity:0}
#fac path{fill:none;stroke:#fff6e2;stroke-width:2.5;stroke-dasharray:3000;stroke-dashoffset:3000;filter:drop-shadow(0 0 6px rgba(237,197,128,.9))}
#laser{position:absolute;left:-40px;top:200px;width:470px;height:5px;border-radius:2px;background:#fff;opacity:0;
  box-shadow:0 0 22px 6px rgba(255,236,200,.9),0 0 60px 16px rgba(237,197,128,.45)}
.spk{position:absolute;left:0;top:0;width:6px;height:6px;border-radius:50%;background:#fff6dc;box-shadow:0 0 10px 3px rgba(237,197,128,.9);opacity:0}
.shd{position:absolute;left:0;top:0;width:26px;height:18px;background:linear-gradient(135deg,#e9edf3,#8e96a3);clip-path:polygon(0 30%,60% 0,100% 70%,35% 100%);opacity:0}
.star{position:absolute;left:0;top:0;width:70px;height:70px;opacity:0;
  background:radial-gradient(circle,#fff 0 6%,rgba(255,255,255,0) 22%),
  linear-gradient(90deg,rgba(255,255,255,0) 0,#fff 50%,rgba(255,255,255,0) 100%) center/100% 3px no-repeat,
  linear-gradient(0deg,rgba(255,255,255,0) 0,#fff 50%,rgba(255,255,255,0) 100%) center/3px 100% no-repeat;
  filter:drop-shadow(0 0 8px rgba(220,235,255,.9))}

.eng{position:absolute;z-index:9;text-align:center;font-weight:600;letter-spacing:.32em;opacity:0;
  background:linear-gradient(100deg,#b8935a 0%,#EDC580 30%,#fff7e4 48%,#EDC580 62%,#a98450 100%);background-size:260% 100%;
  background-position:100% 0;-webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(0 0 14px rgba(237,197,128,.28))}
.eng.big{left:80px;width:460px;top:846px;font-size:36px}
.eng.huge{left:80px;width:480px;top:820px;font-size:118px;font-weight:300;letter-spacing:.22em;line-height:1}
.eng.sub{left:80px;width:480px;top:952px;font-size:26px;letter-spacing:.3em;line-height:1.35;font-weight:600}
.eng.mid{left:0;width:1080px;top:302px;font-size:24px;letter-spacing:.5em}

#rows{position:absolute;left:84px;top:640px;width:446px;z-index:9}
.row{display:flex;align-items:center;gap:18px;height:84px;border-bottom:1px solid rgba(237,197,128,.22);opacity:0}
.row span{font-size:31px;font-weight:600;letter-spacing:.08em;color:#eef3f7}
.rc{width:46px;height:46px;border-radius:50%;border:2px solid #EDC580;display:flex;align-items:center;justify-content:center;flex:none}
.rc .ic{width:28px;height:28px;color:#EDC580;stroke-width:3;opacity:0}

#badge{position:absolute;left:566px;top:306px;width:460px;height:90px;z-index:9;display:flex;align-items:center;gap:16px;opacity:0}
#badge img{width:90px;height:90px}
#badge span{font-size:40px;font-weight:300;letter-spacing:.24em;color:#EDC580}
.bline{position:absolute;left:44px;top:84px;width:2px;height:40px;background:linear-gradient(180deg,#EDC580,rgba(237,197,128,0))}
#ed2{inset:auto;left:560px;top:430px;width:432px;height:580px;opacity:0;z-index:8}
#ed2.win{position:absolute}
#iapill{margin-left:auto;display:flex;align-items:center;gap:8px;padding:4px 14px;border-radius:20px;background:#EDC580;color:#000;font-weight:800;font-size:20px;letter-spacing:.1em;opacity:0}
#iapill i{width:10px;height:10px;border-radius:50%;background:#000;display:block}
#tasks{padding:16px 20px 6px;display:flex;flex-direction:column;gap:8px}
.tk{display:flex;align-items:center;gap:12px;font-size:20px;letter-spacing:.08em;color:#c9d2de;font-weight:600;opacity:0}
.tb{width:28px;height:28px;border-radius:7px;border:2px solid #EDC580;display:flex;align-items:center;justify-content:center}
.tb .ic{width:18px;height:18px;color:#EDC580;stroke-width:3.5;opacity:0}
#codebox{position:absolute;left:0;right:0;top:206px;height:330px;overflow:hidden}
#code,#lzc{font-family:JBM;font-size:18px;line-height:32px;color:#e7ecf3;white-space:nowrap}
.cl{height:32px}
.cl b{color:#EDC580;font-weight:700}.cl em{color:#9fd0ff;font-style:normal}.cl s{color:#6f7a8a;text-decoration:none}.cl u{color:#b9e3a8;text-decoration:none}
#code .cl{opacity:0}
#ticks{position:absolute;right:16px;top:0;width:30px}
.ck{height:32px;display:flex;align-items:center;justify-content:center;opacity:0}
.ck .ic{width:24px;height:24px;color:#EDC580;stroke-width:3.5}
#revis{position:absolute;left:0;right:0;bottom:16px;text-align:center;font-size:30px;font-weight:700;letter-spacing:.42em;color:#EDC580;opacity:0}
#loupe{position:absolute;left:0;top:0;width:200px;height:200px;z-index:10;opacity:0;transform-origin:50% 50%}
#lz{position:absolute;inset:0;border-radius:50%;overflow:hidden;background:#0d1016}
#lzc{position:absolute;left:0;top:0;transform-origin:0 0}
#lring{position:absolute;inset:-10px;border-radius:50%;border:12px solid #c9ced6;
  box-shadow:inset 0 0 0 2px #7d838c,0 0 0 2px #2a2d33,0 18px 40px rgba(0,0,0,.7),inset 0 0 30px rgba(255,255,255,.25)}
#lhandle{position:absolute;left:170px;top:170px;width:90px;height:22px;border-radius:11px;background:linear-gradient(180deg,#d9dde3,#7d838c);transform:rotate(45deg);transform-origin:0 50%}
.chip{position:absolute;left:0;top:0;z-index:11;padding:10px 18px;border-radius:24px;border:1.5px solid #EDC580;background:rgba(10,10,12,.9);
  font-size:20px;font-weight:700;letter-spacing:.1em;color:#EDC580;opacity:0;white-space:nowrap}

#tray{position:absolute;left:95px;top:342px;width:890px;height:222px;z-index:8;display:flex;gap:20px;opacity:0}
.ni{position:relative;width:162px;height:222px;border-radius:14px;background:linear-gradient(180deg,#111217,#07070a);
  border:1px solid rgba(237,197,128,.35);overflow:hidden;opacity:.25}
.nn{position:absolute;left:0;right:0;top:10px;text-align:center;font-size:22px;letter-spacing:.2em;color:#EDC580;font-weight:600}
.nimg{position:absolute;left:11px;top:34px;width:140px;height:140px}
.nl{position:absolute;left:0;right:0;bottom:12px;text-align:center;font-size:15px;letter-spacing:.14em;color:#eef3f7;font-weight:700}
.ncov{position:absolute;left:12px;right:12px;top:42px;height:132px;border-radius:10px;
  background:repeating-linear-gradient(115deg,#15161c 0 6px,#0e0f13 6px 12px);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px}
.ncov .ic{width:40px;height:40px;color:#EDC580}
.ncov span{font-size:36px;color:#9aa3b2;font-weight:300}
#traysheen{position:absolute;top:0;left:-200px;width:160px;height:222px;background:linear-gradient(100deg,rgba(255,255,255,0),rgba(255,255,255,.22),rgba(255,255,255,0));opacity:0}

#cert{position:absolute;left:84px;top:372px;width:452px;height:620px;z-index:9;border-radius:10px;opacity:0;
  background:linear-gradient(180deg,#f4f5f7,#e6e9ee);box-shadow:0 40px 90px rgba(0,0,0,.65);
  outline:2px solid #c9a86a;outline-offset:-16px;padding:46px 44px}
.ct-k{text-align:center;font-size:24px;letter-spacing:.5em;font-weight:700;color:#3a3024}
.ct-line{margin:18px auto 30px;width:220px;height:2px;background:#c9a86a}
.ct-r{display:flex;align-items:center;justify-content:space-between;height:92px;border-bottom:1px solid #cdd2da;opacity:.18}
.ct-r span{font-size:31px;font-weight:700;letter-spacing:.06em;color:#14171c}
.ct-r i{width:48px;height:48px;border-radius:50%;background:#14171c;display:flex;align-items:center;justify-content:center}
.ct-r i .ic{width:30px;height:30px;color:#EDC580;stroke-width:3.2}
#cseal{position:absolute;right:38px;bottom:36px;width:120px;height:120px;opacity:0}
#cseal svg{width:120px;height:120px}
#cseal circle{fill:none;stroke:#b8935a;stroke-width:4}#cseal path{fill:#b8935a}

#case{position:absolute;left:520px;top:300px;width:480px;height:480px;z-index:8}
#boxo,#boxc{position:absolute;left:0;top:0;width:480px;height:480px;opacity:0}
#minidia{position:absolute;left:150px;top:196px;width:96px;height:96px;opacity:0}
#rib{position:absolute;inset:0;opacity:0}
.rv{display:none;position:absolute;left:226px;top:96px;width:30px;height:300px;background:linear-gradient(90deg,#050506,#2a2c33 45%,#050506);transform:scaleY(0);transform-origin:50% 0}
.rh{display:none;position:absolute;left:58px;top:240px;width:366px;height:28px;background:linear-gradient(180deg,#050506,#2a2c33 45%,#050506);transform:scaleX(0);transform-origin:0 50%;transform:skewY(-6deg) scaleX(0)}
.bow{position:absolute;left:198px;top:132px;width:76px;height:76px;border-radius:50%;opacity:0;
  background:radial-gradient(circle at 40% 35%,#f6dfab,#b8935a 70%);box-shadow:0 6px 16px rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center}
.bow .ic{width:38px;height:38px;color:#3a2a12;stroke-width:2.6}
#seal{position:absolute;left:520px;top:796px;width:480px;text-align:center;z-index:9;opacity:0}
#seal .s1{font-size:46px;font-weight:800;letter-spacing:.12em;color:#EDC580}
#seal .s2{margin-top:6px;font-size:22px;font-weight:600;letter-spacing:.55em;color:#eef3f7}
#vital{position:absolute;left:520px;top:906px;width:480px;height:96px;z-index:9;display:flex;align-items:center;justify-content:center;gap:18px;opacity:0}
#vital svg{width:110px;height:56px;overflow:visible}
#inf{fill:none;stroke:#EDC580;stroke-width:5;stroke-dasharray:400;stroke-dashoffset:400;stroke-linecap:round}
#vital span{font-size:28px;font-weight:700;letter-spacing:.16em;color:#eef3f7}
#tagw{left:600px;top:560px;width:330px;height:210px;z-index:10}
#tag{position:absolute;inset:0;transform-style:preserve-3d;opacity:0}
#tstring{position:absolute;left:50px;top:-70px;width:2px;height:80px;background:#c9a86a;transform:rotate(-18deg);transform-origin:50% 100%}
.tf{position:absolute;inset:0;border-radius:14px;backface-visibility:hidden;-webkit-backface-visibility:hidden;
  background:linear-gradient(160deg,#16171c,#060608);border:2px solid #EDC580;box-shadow:0 26px 60px rgba(0,0,0,.7);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px}
.tf.front .ic{width:50px;height:50px;color:#EDC580}
.tf.front span{font-size:34px;font-weight:700;letter-spacing:.28em;color:#eef3f7}
.tf.back{transform:rotateY(180deg)}
.t1{font-size:66px;font-weight:300;letter-spacing:.06em;color:#EDC580;line-height:1}
.t2{font-size:40px;font-weight:700;letter-spacing:.1em;color:#eef3f7;opacity:0}
.t3{font-size:22px;font-weight:700;letter-spacing:.3em;color:#9aa3b2;opacity:0}
#rope{position:absolute;left:520px;top:640px;width:480px;height:320px;z-index:9;opacity:0}
.rp{filter:brightness(1.7) contrast(1.1)}
.rp{position:absolute;left:0;top:0;width:480px;height:320px}
#ropeL{clip-path:inset(0 50% 0 0)}#ropeR{clip-path:inset(0 0 0 50%);transform-origin:92% 85%}
#vip{position:absolute;left:150px;top:150px;width:180px;height:54px;border-radius:8px;background:linear-gradient(180deg,#f3d79b,#b8935a);
  color:#000;font-size:22px;font-weight:800;letter-spacing:.14em;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 24px rgba(0,0,0,.6)}

#btn{position:absolute;left:556px;top:890px;width:420px;height:104px;border-radius:52px;background:#fff;z-index:14;opacity:0;
  display:flex;align-items:center;justify-content:center;gap:18px;box-shadow:0 20px 50px rgba(0,0,0,.6),0 0 0 6px rgba(237,197,128,.35)}
#btn span{font-size:40px;font-weight:800;letter-spacing:.06em;color:#000}
#btn b{font-size:56px;font-weight:500;color:#000;margin-top:-6px}
#tap{position:absolute;left:0;top:0;width:90px;height:90px;border-radius:50%;border:6px solid #fff;opacity:0;z-index:15}
#finger{position:absolute;left:0;top:0;width:100px;height:100px;z-index:16;opacity:0;filter:drop-shadow(0 8px 14px rgba(0,0,0,.7))}
#finger .ic{width:100px;height:100px;stroke:#111;stroke-width:1.4;fill:#fff}
#chev{position:absolute;left:736px;top:996px;width:60px;height:60px;z-index:14;opacity:0;display:flex;flex-direction:column;align-items:center}
#chev .ic{width:44px;height:44px;color:#EDC580;stroke-width:3;margin-top:-22px}
#bellrow{position:absolute;left:540px;top:640px;width:440px;height:110px;z-index:12;opacity:0;border-radius:24px;
  background:rgba(12,12,15,.92);border:1.5px solid rgba(237,197,128,.5);display:flex;align-items:center;gap:18px;padding:0 24px}
#bicon .ic{width:54px;height:54px;color:#EDC580}
#bellrow span{font-size:26px;font-weight:700;letter-spacing:.1em;color:#eef3f7;flex:1}
#tog{width:92px;height:50px;border-radius:25px;background:#2a2d34;position:relative}
#tog i{position:absolute;left:5px;top:5px;width:40px;height:40px;border-radius:50%;background:#fff;display:block}
#env{position:absolute;left:556px;top:590px;width:420px;height:250px;z-index:12;opacity:0;border-radius:14px;
  background:linear-gradient(170deg,#17181d,#060607);border:1.5px solid rgba(237,197,128,.45);overflow:hidden;box-shadow:0 30px 70px rgba(0,0,0,.7)}
#env .flap{position:absolute;left:0;top:0;width:420px;height:150px;background:linear-gradient(180deg,#1f2026,#0d0d10);clip-path:polygon(0 0,100% 0,50% 100%)}
#env .wax{position:absolute;left:176px;top:110px;width:68px;height:68px;border-radius:50%;background:radial-gradient(circle at 40% 35%,#f6dfab,#b8935a 70%);
  color:#3a2a12;font-size:34px;font-weight:800;display:flex;align-items:center;justify-content:center}
#env span{position:absolute;left:0;right:0;bottom:18px;text-align:center;font-size:20px;font-weight:700;letter-spacing:.16em;color:#eef3f7;line-height:1.35}
#fin{position:absolute;left:540px;top:620px;width:440px;z-index:12;opacity:0;text-align:center}
#fin .f1{font-size:58px;font-weight:300;letter-spacing:.06em;color:#EDC580}
#fin .f2{margin-top:10px;font-size:22px;font-weight:700;letter-spacing:.16em;color:#eef3f7}

#endt{position:absolute;left:0;width:1080px;top:836px;text-align:center;z-index:12;opacity:0}
#endt .e1{font-size:72px;font-weight:800;letter-spacing:.1em;color:#EDC580}
#endt .e2{margin-top:8px;font-size:30px;font-weight:600;letter-spacing:.32em;color:#eef3f7}
#endl{position:absolute;left:0;width:1080px;top:1106px;text-align:center;font-size:30px;font-weight:600;color:#e3e8ee;z-index:12;opacity:0}
#sealfinal{position:absolute;inset:0;background:#03090E;z-index:13;opacity:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px}
.sf1{font-size:54px;font-weight:700;color:#EDC580;letter-spacing:.02em;margin-top:-260px}
.sf2{font-size:60px;font-weight:300;color:#eef3f7;letter-spacing:.08em}

.caption{left:120px;top:1046px;width:840px;height:104px;z-index:30;display:flex;align-items:center;justify-content:center}
.cap{width:840px;text-align:center;font-family:Geist;font-weight:800;line-height:1.1;text-transform:uppercase;letter-spacing:.01em;
  color:#fff;white-space:nowrap;text-shadow:0 4px 16px rgba(0,0,0,.85),0 0 2px rgba(0,0,0,.9);opacity:0;visibility:hidden}
.cap .w{display:inline-block;margin:0 .03em;padding:.02em .1em;border-radius:.16em;transform-origin:50% 70%}
#grain{position:absolute;left:-256px;top:-256px;width:1592px;height:2432px;background:url('assets/grain.png');opacity:.06;z-index:40;pointer-events:none;mix-blend-mode:overlay}
#flash{position:absolute;inset:0;background:#fff;opacity:0;z-index:45;pointer-events:none}
#black{position:absolute;inset:0;background:#000;opacity:0;z-index:44;pointer-events:none}
"""

JS = r"""
const tl=gsap.timeline({paused:true});
const K=window.K;const D=K.duration;const E={immediateRender:false};
const S=(s,v,t)=>tl.set(s,v,t);
const TO=(s,v,t)=>tl.to(s,v,t);
const FT=(s,a,b,t)=>tl.fromTo(s,a,Object.assign({},E,b),t);
let seed=K.seed;function rnd(){seed=(seed*1664525+1013904223)%4294967296;return seed/4294967296;}
const R=K.rig, SX=K.spotx;
function on(s,t,d,v){FT(s,Object.assign({opacity:0},v&&v.from||{}),Object.assign({opacity:1,duration:d||.3,ease:'power2.out'},v&&v.to||{}),t);}
function off(s,t,d,v){TO(s,Object.assign({opacity:0,duration:d||.22,ease:'power2.in'},v||{}),t);}
function rig(st,t,d){TO('#prig',Object.assign({duration:d||.6,ease:'expo.inOut'},R[st]),t);TO('#spot',{x:SX[st]-540,duration:d||.6,ease:'expo.inOut'},t);}
function flash(t,p,d){FT('#flash',{opacity:p},{opacity:0,duration:d||.22,ease:'power2.out'},t);}
function punch(t,s,hold,back){TO('#pp',{scale:s,duration:.14,ease:'power4.out'},t-.04);TO('#pp',{scale:back||1,duration:.5,ease:'power3.inOut'},t+hold);}
function shake(t,a){[[a,-a*.6],[-a*.8,a*.5],[a*.5,a*.4],[-a*.3,-a*.3],[0,0]].forEach((p,i)=>TO('#objs-shake',{x:p[0],y:p[1],duration:.035},t+i*.035));}
function typeIn(sel,t,dur){const ch=document.querySelectorAll(sel+' .ch');const n=ch.length;ch.forEach((c,i)=>S(c,{opacity:1},t+dur*i/n));}
function sheen(sel,t,d){FT(sel,{backgroundPosition:'100% 0'},{backgroundPosition:'0% 0',duration:d||1.4,ease:'power2.inOut'},t);}

// ---------- initial state (outside the timeline: frame 0 must already show the hook)
gsap.set('#prig',R.right);gsap.set('#spot',{x:SX.right-540});
gsap.set(['#hdr','#ped','#stone','#dia','#fac','#laser','#lb-bruto','#lb-prd','#lb-prd2','.row','#badge','#ed2','#loupe','.chip',
  '#wtitle','#tray','#cert','#boxo','#boxc','#minidia','#rib','#seal','#vital','#tag','#rope','#btn','#chev','#bellrow','#env','#fin',
  '#endt','#endl','#sealfinal','.plq','.glyph','#shw','#crt','#black','#flash','#rim'],{opacity:0});
gsap.set('#cone,#halo',{opacity:.0});gsap.set('.glyph',{opacity:0});gsap.set('#dust',{opacity:0});
gsap.set('#edprog',{scaleX:.35});gsap.set('#ed',{opacity:1,rotationY:13,rotationX:2,transformOrigin:'0% 50%'});gsap.set('#sheet',{rotationY:11,rotationX:3,transformOrigin:'0% 50%'});gsap.set('#edw',{opacity:1});gsap.set('#cur',{opacity:0});
gsap.set('#platew',{opacity:1});gsap.set('#pbox',{opacity:1});gsap.set('#hook',{opacity:1});gsap.set('#floorword',{opacity:1});gsap.set('#mark',{opacity:.9});

// dust in the spot: seeded drift
document.querySelectorAll('#dust .d').forEach((el)=>{const x=rnd()*600,y=rnd()*1150,s=.5+rnd()*1.3;
  gsap.set(el,{x:x,y:y,scale:s,opacity:.25+rnd()*.6});
  TO(el,{x:x+(rnd()*80-40),y:y-60-rnd()*140,duration:D,ease:'none'},0);});
TO('#grain',{x:256,y:256,duration:D,ease:'steps('+Math.round(D*15)+')'},0);

// jump cuts: alternate 1.0/1.035 at each junction, around the face
K.junctions.forEach((j,i)=>{S('#pj',{scale:(i%2?1.035:1)},j);});
// slow breathing of the presenter
FT('#pp',{scale:1},{scale:1.02,duration:6.2,ease:'sine.inOut'},0);

// floor words (atmosphere under the ad UI): engraved, in perspective, one per act
const FW=K.floor;
function fwSize(t){return Math.min(170,840/(0.66*t.length));}
gsap.set('#fw',{fontSize:fwSize(K.text.floor0)});
S('#floorword',{opacity:0},K.p0);
FW.forEach((f)=>{S('#fw',{textContent:f[1],fontSize:fwSize(f[1])},f[0]-.02);FT('#floorword',{opacity:0,y:30},{opacity:1,y:0,duration:.5,ease:'power2.out'},f[0]);});
off('#floorword',K.voice_end-.2,.3);
// ---------- HOOK: the code editor that will not open
typeIn('#edtab',K.tab-.05,.55);
gsap.set('#ed .splash',{opacity:0});gsap.set('#ed .ghost',{opacity:0});
document.querySelectorAll('#edcode .cl').forEach((el,i)=>{if(i<3){gsap.set(el,{opacity:1});}else{S(el,{opacity:1},0.15+(i-3)*.45);}});
FT('#hook .h2 b',{opacity:1},{opacity:.15,duration:.35,yoyo:true,repeat:7},0.2);
FT('#ed',{rotationY:13,y:0},{rotationY:9,y:-12,duration:K.freeze,ease:'sine.inOut'},0);
FT('#edcode',{opacity:1},{opacity:.45,duration:.25},K.freeze);
on('#cur',K.cursor-.3,.2);
FT('#cur',{x:0,y:0},{x:-382,y:-398,duration:K.close-K.cursor+.1,ease:'power2.inOut'},K.cursor-.25);
TO('#cur',{scale:.82,duration:.07},K.close+.08);TO('#cur',{scale:1,duration:.12},K.close+.15);
S('#edx',{boxShadow:'0 0 0 6px rgba(255,95,87,.45)'},K.close+.08);
// CRT-style collapse: window squeezes to a line, then to a dot
TO('#ed',{scaleY:.012,duration:.16,ease:'power4.in'},K.close+.18);
on('#crt',K.close+.30,.04);off('#ed',K.close+.34,.01);
TO('#crt',{scaleX:.02,duration:.16,ease:'power3.in'},K.close+.36);off('#crt',K.close+.52,.06);
off('#cur',K.close+.3,.15);
off('#mark',K.close+.4,.2);FT('#fw',{opacity:1},{opacity:.2,duration:.06,yoyo:true,repeat:3},K.close+.1);

// ---------- BLACKOUT (declared pause) and the spotlight
S('#black',{opacity:1},K.p0);S('#platew',{opacity:0},K.p0);S('#hook',{opacity:0},K.p0);S('#prig',R.full,K.p0+.02);S('#spot',{x:0},K.p0+.02);
S('#black',{opacity:0},K.p1);
FT('#cone',{opacity:0},{opacity:1,duration:.05},K.p1);TO('#cone',{opacity:.35,duration:.04},K.p1+.09);TO('#cone',{opacity:1,duration:.05},K.p1+.15);
FT('#halo',{opacity:0},{opacity:1,duration:.3},K.p1);FT('#dust',{opacity:0},{opacity:1,duration:.8},K.p1+.05);
FT('#rim',{opacity:0},{opacity:1,duration:.4},K.p1);FT('#pool',{opacity:0},{opacity:1,duration:.5},K.p1);
punch(K.spot_punch,1.07,.7);

// two plaques, flanking
FT('#pl1',{opacity:0,y:-40},{opacity:1,y:0,duration:.35,ease:'expo.out'},K.plaque1-.02);
FT('#pl2',{opacity:0,y:-40},{opacity:1,y:0,duration:.35,ease:'expo.out'},K.plaque2);
sheen('#pl1 .pk',K.plaque_sheen,1);
// no line of code: the glyph is cut by light; the gear too
FT('#gcode',{opacity:0,scale:.7},{opacity:1,scale:1,duration:.3,ease:'back.out(2)'},K.glyph1-.05);
FT('#gcode .slash',{scaleX:0},{scaleX:1,duration:.16,ease:'power3.out'},K.cut1-.04);
TO('#gcode .gh.a',{x:-24,y:-30,rotation:-12,opacity:0,duration:.7,ease:'power2.in'},K.cut1+.14);
TO('#gcode .gh.b',{x:20,y:140,rotation:18,opacity:0,duration:.7,ease:'power2.in'},K.cut1+.14);
off('#gcode .slash',K.cut1+.25,.3);
FT('#ggear',{opacity:0,scale:.7},{opacity:1,scale:1,duration:.3,ease:'back.out(2)'},K.glyph2-.05);
FT('#ggear .slash',{scaleX:0},{scaleX:1,duration:.16,ease:'power3.out'},K.cut2-.02);
TO('#ggear .gh.a',{x:24,y:-30,rotation:12,opacity:0,duration:.7,ease:'power2.in'},K.cut2+.16);
TO('#ggear .gh.b',{x:-20,y:140,rotation:-18,opacity:0,duration:.7,ease:'power2.in'},K.cut2+.16);
off('#ggear .slash',K.cut2+.3,.3);
on('#pl1 .ps',K.cut1+.2,.3);on('#pl2 .ps',K.cut2+.25,.3);

// ---------- STEP 1: plain text editor -> raw prompt
off('#pl2',K.step1-.3,.25);off('#pl1',K.step1-.3,.25);
rig('right',K.step1-.2,.6);
S('#hdr-t',{textContent:K.text.step1},K.step1-.1);
FT('#hdr',{opacity:0,x:-30},{opacity:1,x:0,duration:.4,ease:'expo.out'},K.step1+.15);
FT('#shw',{opacity:0,y:60,rotationX:-20},{opacity:1,y:0,rotationX:0,duration:.5,ease:'expo.out'},K.sheet);
on('#caret',K.caret-.2,.1);
const lines=[['#sl1',K.line1],['#sl2',K.line2-.5],['#sl3',K.line3],['#sl4',K.line4],['#sl5',K.line5]];
lines.forEach((l,i)=>{const dur=Math.max(.35,(i+1<lines.length?lines[i+1][1]:K.lines_end+.5)-l[1]-.1);
  typeIn(l[0],l[1]-.05,Math.min(dur,.9));
  S('#caret',{x:0,y:i*42+4},l[1]-.06);});
document.querySelectorAll('.fl').forEach((el,i)=>{S(el,{opacity:1},K.line5+.4+i*.06);});
FT('#caret',{opacity:1},{opacity:0,duration:.08,repeat:12,yoyo:true},K.caret);
// compaction: all text sucked to the centre -> the raw stone appears and drops on the velvet
TO('#sheet .sl, #sheet .fl',{scale:.2,x:120,y:140,opacity:0,duration:.45,ease:'power3.in',stagger:.015},K.compact);
TO('#sheet',{scale:.15,rotation:-25,opacity:0,duration:.5,ease:'power3.in'},K.compact+.2);
S('#shw',{opacity:0},K.compact+.72);
FT('#stone',{opacity:0,scale:.25,y:-60,filter:'blur(10px)'},{opacity:1,scale:1,y:-50,filter:'blur(0px)',duration:.4,ease:'power2.out'},K.compact+.55);
TO('#stone',{y:0,duration:.28,ease:'bounce.out'},K.land-.12);
FT('#ped',{opacity:0},{opacity:1,duration:.3},K.land);FT('#ospot',{opacity:0},{opacity:1,duration:.4},K.compact+.5);off('#ospot',K.machine-.2,.3);
shake(K.land+.05,7);
FT('#lb-bruto',{opacity:0,y:16},{opacity:1,y:0,duration:.4,ease:'power2.out'},K.land+.12);sheen('#lb-bruto',K.land+.2,1.4);

// ---------- STEP 2: the cut
S('#hdr-t',{textContent:K.text.step2},K.step2);FT('#hdr',{opacity:.2},{opacity:1,duration:.3},K.step2);
TO('#gem',{scale:1.05,duration:K.laser-K.step2,ease:'sine.inOut'},K.step2);
off('#lb-bruto',K.step2-.05,.3);
FT('#laser',{opacity:0,y:-150,rotation:-14},{opacity:1,y:-150,rotation:-14,duration:.08},K.laser-.05);
TO('#laser',{y:150,rotation:10,duration:(K.flash-K.laser)*.5,ease:'sine.inOut',yoyo:true,repeat:1},K.laser);
off('#laser',K.flash+.05,.08);
FT('#fac',{opacity:0},{opacity:1,duration:.2},K.laser);
FT('#fac path',{strokeDashoffset:3000},{strokeDashoffset:0,duration:K.flash-K.laser,ease:'none'},K.laser);
document.querySelectorAll('.spk').forEach((el,i)=>{const t=K.laser+(K.flash-K.laser)*i/16;const x=60+rnd()*290,y=60+rnd()*290;
  FT(el,{opacity:1,x:x,y:y,scale:1},{opacity:0,x:x+(rnd()*160-80),y:y+60+rnd()*120,scale:.3,duration:.5,ease:'power2.out'},t);});
document.querySelectorAll('.shd').forEach((el,i)=>{const t=K.shards+(K.flash-K.shards)*i/10;const x=80+rnd()*250,y=80+rnd()*250;
  FT(el,{opacity:1,x:x,y:y,rotation:0},{opacity:0,x:x+(x>205?140:-140)+rnd()*60,y:y+260,rotation:rnd()*360,duration:.8,ease:'power2.in'},t);});
// flash -> the brilliant
flash(K.flash+.02,.9,.35);
S('#stone',{opacity:0},K.flash+.04);S('#fac',{opacity:0},K.flash+.04);S('#gem',{scale:1},K.flash+.04);
FT('#dia',{opacity:0,scale:1.12},{opacity:1,scale:1,duration:.6,ease:'expo.out'},K.flash+.04);
const SP=[[300,90],[110,140],[250,250],[160,300],[330,210],[80,230],[205,60]];
document.querySelectorAll('.star').forEach((el,i)=>{const t=K.flash+.15+i*.33;
  FT(el,{opacity:0,scale:.2,rotation:0,x:SP[i][0]-35,y:SP[i][1]-35},{opacity:1,scale:1.15,rotation:45,duration:.22,ease:'power2.out'},t);
  TO(el,{opacity:0,scale:.3,duration:.35},t+.25);
  FT(el,{opacity:0,scale:.2},{opacity:.9,scale:1,duration:.2},t+2.4);TO(el,{opacity:0,duration:.3},t+2.65);});
punch(K.flash+.04,1.05,.5);
FT('#lb-prd',{opacity:0,scale:.9},{opacity:1,scale:1,duration:.45,ease:'expo.out'},K.title-.05);sheen('#lb-prd',K.title+.1,1.6);
FT('#lb-prd2',{opacity:0,y:10},{opacity:1,y:0,duration:.4},K.subtitle-.05);
// the PRD as a document: the brilliant goes up, its sections light one by one
TO('#gem',{scale:.5,x:-125,y:-167,duration:.6,ease:'expo.inOut'},K.doc-.1);
TO('#lb-prd',{x:118,y:-452,scale:.55,duration:.6,ease:'expo.inOut'},K.doc-.1);off('#lb-prd2',K.doc-.1,.2);
const RW=[['#r1',K.doc+.35],['#r2',K.row2],['#r3',K.row3-.05],['#r4',K.row4]];
RW.forEach((r)=>{FT(r[0],{opacity:0,x:-30},{opacity:1,x:0,duration:.3,ease:'power3.out'},r[1]-.1);
  FT(r[0]+' .rc .ic',{opacity:0,scale:.4},{opacity:1,scale:1,duration:.22,ease:'back.out(3)'},r[1]+.2);});
TO('#r1,#r2',{opacity:.55,duration:.3},K.rows_dim);

// ---------- AI: only then the editor comes back
off('#rows',K.machine-.2,.25);off('#lb-prd',K.machine-.2,.25);off('#hdr',K.machine-.2,.25);
TO('#gem',{x:470,y:-300,scale:.2,opacity:0,duration:.6,ease:'expo.inOut'},K.machine-.2);
rig('left',K.machine-.1,.6);
FT('#badge',{opacity:0,x:40},{opacity:1,x:0,duration:.4,ease:'expo.out'},K.machine+.35);
FT('#ed2',{opacity:0,scaleY:.02},{opacity:1,scaleY:1,duration:.35,ease:'expo.out'},K.machine_on-.15);
FT('#iapill',{opacity:0,scale:.5},{opacity:1,scale:1,duration:.3,ease:'back.out(2.5)'},K.pill);
FT('#iapill i',{opacity:1},{opacity:.2,duration:.4,yoyo:true,repeat:14},K.pill+.3);
// demands fly from the PRD badge into the editor task list
const CP=[['#cp1','#tk1'],['#cp2','#tk2'],['#cp3','#tk3']];
CP.forEach((c,i)=>{const t=K.tasks+i*.22;
  FT(c[0],{opacity:0,x:600,y:330,scale:.8},{opacity:1,x:640,y:360,scale:1,duration:.15},t);
  TO(c[0],{x:560,y:440+i*36,scale:.7,opacity:0,duration:.35,ease:'power3.in'},t+.18);
  FT(c[1],{opacity:0,x:-14},{opacity:1,x:0,duration:.2},t+.5);
  FT(c[1]+' .tb .ic',{opacity:0,scale:.3},{opacity:1,scale:1,duration:.2,ease:'back.out(3)'},K.loupe+.3+i*.5);});
// code is generated
document.querySelectorAll('#code .cl').forEach((el,i)=>{S(el,{opacity:1},K.code-.1+i*.11);});
// review: the jeweller's loupe sweeps the lines; each reviewed line gets a check
const LX=592,LY0=636,STEP=32,NL=7;
FT('#loupe',{opacity:0,x:LX+150,y:LY0-40,scale:.5},{opacity:1,x:LX+150,y:LY0-40,scale:.8,duration:.3,ease:'back.out(2)'},K.loupe-.15);
gsap.set('#lzc',{scale:1.7});
for(let i=0;i<NL;i++){const t=K.loupe+.2+i*.24;const cy=LY0+i*STEP+60-100;
  TO('#loupe',{y:cy,scale:.8,duration:.22,ease:'power2.inOut'},t);
  TO('#lzc',{x:100-1.7*(LX+150+100-560),y:100-1.7*(cy+100-636),duration:.22,ease:'power2.inOut'},t);
  FT('#ck'+i,{opacity:0,scale:.4},{opacity:1,scale:1,duration:.16,ease:'back.out(3)'},t+.16);}
S('#lzc',{x:100-1.7*(LX+150+100-560),y:100-1.7*(LY0-40+100-636)},K.loupe-.16);
FT('#revis',{opacity:0,scale:1.3},{opacity:1,scale:1,duration:.22,ease:'power4.out'},K.stamp-.05);
off('#loupe',K.stamp+.25,.25);

// ---------- VITRINE: it was only a summary
TO('#ed2',{scale:.3,x:-280,y:-240,opacity:0,duration:.55,ease:'expo.in'},K.tray-.15);off('#badge',K.tray-.15,.3);
rig('low',K.tray-.05,.7);
FT('#wtitle',{opacity:0,letterSpacing:'.9em'},{opacity:1,letterSpacing:'.5em',duration:.7,ease:'expo.out'},K.tray_title-.05);
FT('#tray',{opacity:0,y:40},{opacity:1,y:0,duration:.5,ease:'expo.out'},K.tray_in);
for(let i=0;i<5;i++){FT('#ni'+i,{opacity:.25},{opacity:1,duration:.18},K.niches+i*.14);
  FT('#ni'+i,{boxShadow:'0 0 0 0 rgba(237,197,128,0)'},{boxShadow:'0 0 26px 2px rgba(237,197,128,.45)',duration:.18,yoyo:true,repeat:1},K.niches+i*.14);}
FT('#traysheen',{opacity:1,x:0},{opacity:1,x:1250,duration:.55,ease:'power2.inOut'},K.tray_sheen-.2);

// ---------- CERTIFICATE
TO('#tray',{y:-60,opacity:0,duration:.4,ease:'power3.in'},K.cert-.3);off('#wtitle',K.cert-.3,.3);
rig('right',K.cert-.25,.6);
FT('#cert',{opacity:0,y:120,rotation:-4},{opacity:1,y:0,rotation:-1.5,duration:.55,ease:'expo.out'},K.cert);
[['#c1',K.cert1],['#c2',K.cert2],['#c3',K.cert3]].forEach((c)=>{
  FT(c[0],{opacity:.18},{opacity:1,duration:.15},c[1]-.05);
  FT(c[0]+' i',{scale:1.6},{scale:1,duration:.22,ease:'back.out(3)'},c[1]+.05);});
FT('#cseal',{opacity:0,scale:1.8,rotation:-30},{opacity:1,scale:1,rotation:-12,duration:.18,ease:'power4.in'},K.cert_seal+.1);

// ---------- THE CASE
TO('#cert',{x:-520,rotation:-8,opacity:0,duration:.5,ease:'expo.in'},K.case-.25);
rig('left',K.case-.1,.6);
FT('#boxo',{opacity:0,scale:.92,y:30},{opacity:1,scale:1,y:0,duration:.55,ease:'expo.out'},K.case_open-.2);
FT('#minidia',{opacity:0,x:-300,y:-120,scale:2.2},{opacity:1,x:0,y:0,scale:1,duration:.55,ease:'power3.inOut'},K.case_gem);
FT('#minidia',{filter:'brightness(1)'},{filter:'brightness(1.6)',duration:.3,yoyo:true,repeat:1},K.case_glow);
FT('#seal',{opacity:0,y:20},{opacity:1,y:0,duration:.45,ease:'expo.out'},K.case_seal-.05);
FT('#seal .s1',{letterSpacing:'.3em'},{letterSpacing:'.12em',duration:.6,ease:'expo.out'},K.case_seal-.05);
FT('#vital',{opacity:0},{opacity:1,duration:.3},K.forever);
FT('#inf',{strokeDashoffset:400},{strokeDashoffset:0,duration:.7,ease:'power2.inOut'},K.forever);
// "mas atenção": the case slams shut
FT('#cone',{opacity:1},{opacity:.25,duration:.05,yoyo:true,repeat:3},K.flicker);
S('#boxo',{opacity:0},K.slam-.02);S('#minidia',{opacity:0},K.slam-.02);S('#boxc',{opacity:1},K.slam-.02);
FT('#case',{y:-14},{y:0,duration:.25,ease:'bounce.out'},K.slam-.02);
off('#vital',K.slam,.2);off('#seal',K.slam,.2);
punch(K.slam,1.06,.45);

// ---------- THE CONDITION: ribbon, sealed tag
FT('#rib',{opacity:0},{opacity:1,duration:.05},K.slam+.3);
FT('#rib .rv',{scaleY:0},{scaleY:1,duration:.4,ease:'power3.out'},K.slam+.4);
FT('#rib .rh',{scaleX:0,skewY:-6},{scaleX:1,skewY:-6,duration:.4,ease:'power3.out'},K.slam+.6);
FT('#rib .bow',{opacity:0,scale:2.2},{opacity:1,scale:1,duration:.22,ease:'power4.in'},K.slam+.35);
FT('#tag',{opacity:0,y:-40,rotation:-8},{opacity:1,y:0,rotation:-3,duration:.5,ease:'back.out(1.6)'},K.tag-.1);
TO('#tag',{rotation:2,duration:1.1,ease:'sine.inOut',yoyo:true,repeat:2},K.tag+.45);
TO('#tag',{rotationY:180,duration:.45,ease:'power3.inOut'},K.flip);
FT('#t2',{opacity:0},{opacity:1,duration:.25},K.tag_time-.05);
FT('#t3',{opacity:0},{opacity:1,duration:.25},K.tag_note-.05);
// velvet rope with the VIP plate (the tag leaves first)
TO('#tag',{opacity:0,y:-30,duration:.25},K.rope-.3);
FT('#rope',{opacity:0,y:60},{opacity:1,y:0,duration:.5,ease:'expo.out'},K.rope);
FT('#vip',{opacity:0,scale:.6},{opacity:1,scale:1,duration:.3,ease:'back.out(2.5)'},K.vip_plate-.05);
sheen('#vip',K.vip_sheen,.8);

// ---------- CTA

TO('#case',{scale:.62,y:-92,duration:.5,ease:'expo.inOut'},K.cta-.2);
TO('#rope',{y:-80,scale:.9,duration:.5,ease:'expo.inOut'},K.cta-.2);
FT('#vip',{boxShadow:'0 0 0 0 rgba(243,215,155,0)'},{boxShadow:'0 0 30px 8px rgba(243,215,155,.7)',duration:.3,yoyo:true,repeat:3},K.cta);
FT('#btn',{opacity:0,scale:.6},{opacity:1,scale:1,duration:.26,ease:'back.out(2.2)'},K.button-.08);
FT('#finger',{opacity:0,x:960,y:1000},{opacity:1,x:905,y:925,duration:.28,ease:'power3.out'},K.button-.25);
TO('#finger',{scale:.85,duration:.06},K.button+.08);TO('#finger',{scale:1,duration:.12},K.button+.15);
FT('#tap',{opacity:.9,scale:.3,x:905,y:897},{opacity:0,scale:2.4,x:905,y:897,duration:.45,ease:'power2.out'},K.button+.1);
FT('#btn',{scale:.95},{scale:1,duration:.2},K.button+.1);
off('#finger',K.button+.55,.2);
on('#chev',K.button+.25,.2);FT('#chev',{y:-8},{y:8,duration:.42,ease:'sine.inOut',yoyo:true,repeat:Math.floor((K.voice_end-K.button)/.42)},K.button+.25);
// the rope opens: the right half swings away
TO('#ropeR',{x:110,opacity:0,duration:.55,ease:'power3.in'},K.rope_open);TO('#ropeL',{x:-110,opacity:0,duration:.55,ease:'power3.in'},K.rope_open);
TO('#vip',{y:60,opacity:0,duration:.4,ease:'power2.in'},K.rope_open);
TO('#case',{filter:'brightness(1.35)',duration:.4,yoyo:true,repeat:1},K.rope_open+.1);
FT('#bellrow',{opacity:0,y:30},{opacity:1,y:0,duration:.35,ease:'expo.out'},K.bell-.15);
TO('#tog',{backgroundColor:'#EDC580',duration:.15},K.toggle);TO('#tog i',{x:42,duration:.15,ease:'power3.out'},K.toggle);
FT('#bicon',{rotation:0},{rotation:16,duration:.07,yoyo:true,repeat:7,ease:'sine.inOut'},K.toggle+.1);
TO('#bellrow',{opacity:0,y:-30,duration:.25},K.envelope-.15);
FT('#env',{opacity:0,x:120,rotation:6},{opacity:1,x:0,rotation:-2,duration:.45,ease:'expo.out'},K.envelope);
FT('#env .wax',{scale:1.5},{scale:1,duration:.2,ease:'power4.in'},K.envelope_seal);
TO('#env',{opacity:0,x:-80,duration:.3},K.fin-.2);
FT('#fin',{opacity:0,y:20},{opacity:1,y:0,duration:.4,ease:'expo.out'},K.fin);
FT('#fin .f2',{opacity:0},{opacity:1,duration:.3},K.fin_line-.05);
punch(K.final_punch,1.05,.4);

// ---------- END CARD
const C=K.voice_end;
off('#pbox',C-.25,.25);off('#cone',C,.4);off('#halo',C,.4);off('#rim',C-.2,.3);off('#pool',C-.2,.3);
off('#fin',C-.2,.2);off('#chev',C-.1,.1);off('#rope',C-.2,.2);
TO('#case',{x:-230,y:10,scale:1.04,duration:.6,ease:'expo.inOut'},C-.1);
TO('#btn',{x:-216,y:105,duration:.6,ease:'expo.inOut'},C-.1);
FT('#endt',{opacity:0,y:24},{opacity:1,y:0,duration:.5,ease:'expo.out'},C+.35);sheen('#endt .e1',C+.6,1.4);
FT('#endl',{opacity:0},{opacity:1,duration:.4},C+.8);
FT('#btn',{boxShadow:'0 0 0 0px rgba(237,197,128,.55)'},{boxShadow:'0 0 0 18px rgba(237,197,128,0)',duration:.8,repeat:2},C+.9);
FT('#sealfinal',{opacity:0},{opacity:1,duration:.3,ease:'power2.out'},D-1.0);
S('#btn',{zIndex:16},D-1.0);
"""


def page(k, caps, kjs, T):
    plugins = ""
    return f"""<!doctype html><html lang="pt"><head><meta charset="utf-8"><title>lapidacao</title>
<script src="assets/gsap.min.js"></script>{plugins}<style>{CSS}</style></head><body>
<main id="stage" data-composition-id="main" data-start="0" data-duration="{k['duration']:.4f}" data-width="1080" data-height="1920" data-fps="30">
<div id="objs-shake" style="position:absolute;inset:0">
{scenes(T)}
<div id="prig"><div id="pj"><div id="pp">
  <div id="rim"></div>
  <div id="platew"><video id="plate" class="clip" data-start="0" data-duration="{k['voice_end']:.4f}" data-track-index="1" src="assets/camera-hd.mp4" muted playsinline></video></div>
  <div id="pbox"><video id="alpha" class="clip" data-start="0" data-duration="{k['voice_end']:.4f}" data-track-index="2" src="assets/camera-alpha.webm" muted playsinline></video></div>
</div></div></div>
</div>
{caption_html(caps)}
<div id="grain"></div><div id="black"></div><div id="flash"></div>
<audio id="master" class="clip" data-start="0" data-duration="{k['duration']:.4f}" data-track-index="100" src="assets/master.wav" data-volume="1"></audio>
</main>
<script>window.K={json.dumps(kjs, ensure_ascii=False)};</script>
<script>{JS}{rk.captions_js(caps, mode="pill", pill=("#000000", "#F3D79B"))}window.__timelines=window.__timelines||{{}};window.__timelines.main=tl;</script>
</body></html>"""


# ------------------------------------------------------------------ sound
def sfx_lib():
    return lk.sfx_library(rk, WORK)


def sound_events(k):
    E = []

    def ev(t, cat, gain, ctx, var=0, length=None, rate=1.0):
        e = {"time": round(max(0.0, t), 3), "category": cat, "variant": var, "gain_db": gain, "context": ctx}
        if length:
            e["length"] = length
        if rate != 1.0:
            e["rate"] = rate
        E.append(e)

    ev(0.0, "s_typing", -27, "editor abrindo: teclado ao fundo", 0, 3.4)
    ev(k["freeze"] - 0.05, "s_ui", -24, "barra congela")
    ev(k["close"] + 0.08, "s_click", -18, "clique no fechar", 0, 0.2)
    ev(k["close"] + 0.18, "s_power_down", -16, "editor implode (CRT)")
    ev(k["p0"], "s_switch", -9, "apagão: interruptor pesado", 0, 0.45)
    ev(k["p0"], "s_sub", -10, "apagão: grave", 0, 0.5)
    ev(k["p1"] - 0.02, "s_spot", -12, "spot acende")
    ev(k["p1"] + 0.05, "s_shimmer", -28, "poeira no feixe", 0, 1.6)
    ev(k["plaque1"] - 0.04, "s_lock", -24, "placa 01", 0, 0.3)
    ev(k["plaque2"] - 0.02, "s_lock", -24, "placa 02", 1, 0.3)
    ev(k["glyph1"] - 0.06, "s_lift", -24, "</> aparece", 0, 0.6)
    ev(k["cut1"] - 0.06, "s_glass", -17, "</> cortado pela luz", 0, 0.9)
    ev(k["cut2"] - 0.04, "s_glass", -19, "engrenagem cortada", 0, 0.9, 1.08)
    ev(k["step1"] - 0.22, "s_velvet", -20, "troca de plano: PASSO 01")
    ev(k["sheet"] - 0.04, "s_paper", -20, "folha do editor de texto entra", 0, 0.7)
    ev(k["line1"] - 0.05, "s_typing", -27, "digitando o prompt bruto", 1, 5.6)
    ev(k["compact"] + 0.0, "s_vacuum", -16, "texto sugado para o centro", 0, 1.0)
    ev(k["land"] - 0.10, "s_impact", -11, "pedra bruta cai no veludo", 0, 1.0)
    ev(k["land"] - 0.10, "s_sub", -14, "baque grave", 0, 0.6)
    ev(k["step2"] - 0.05, "s_tick", -22, "PASSO 02")
    ev(k["riser"] + 0.25, "s_riser", -20, "suspense antes de refinar", 1, 0.55)
    ev(k["laser"] - 0.06, "s_laser", -21, "laser de lapidação")
    ev(k["laser"] + 0.10, "s_grind", -25, "esmeril")
    ev(k["flash"] + 0.0, "s_glass", -12, "flash: o diamante", 0, 1.4)
    ev(k["flash"] + 0.02, "s_crystal", -16, "brilho do diamante", 0)
    ev(k["flash"] + 0.5, "s_sparkle", -29, "estrelas de brilho", 0, 1.8)
    ev(k["title"] - 0.08, "s_crystal", -22, "PRD gravado", 1)
    ev(k["doc"] - 0.12, "s_velvet", -22, "o PRD vira documento")
    for i, key in enumerate(("doc", "row2", "row3", "row4")):
        t = k[key] + (0.35 if key == "doc" else 0) + 0.12
        ev(t, "s_crystal", -27, f"linha do PRD {i + 1}", i % 3)
    ev(k["machine"] - 0.15, "s_velvet", -20, "troca de plano: a IA")
    ev(k["machine_on"] - 0.15, "s_power_up", -20, "editor volta a ligar", 0, 1.1)
    ev(k["pill"] - 0.02, "s_click", -24, "selo IA", 2, 0.2)
    for i in range(3):
        ev(k["tasks"] + i * 0.22, "s_click", -27, f"demanda {i + 1} entra", 1, 0.15)
    ev(k["code"] - 0.12, "s_typing", -27, "código sendo gerado", 1, 1.5)
    ev(k["loupe"] - 0.15, "s_shutter", -24, "lupa do joalheiro")
    for i in range(7):
        ev(k["loupe"] + 0.36 + i * 0.24, "s_tick", -30, f"linha revisada {i + 1}")
    ev(k["stamp"] - 0.06, "s_staple", -22, "REVISADO", 0, 0.3)
    ev(k["tray"] - 0.2, "s_vacuum", -21, "recua para a vitrine", 0, 1.0)
    for i in range(5):
        ev(k["niches"] + i * 0.14 - 0.02, "s_lock", -27, f"nicho {i + 1}", i % 2, 0.25)
    ev(k["tray_sheen"] - 0.22, "s_sparkle", -29, "brilho passa na bandeja", 0, 0.9)
    ev(k["cert"] - 0.05, "s_paper", -20, "certificado desliza", 2, 0.8)
    ev(k["cert1"] - 0.04, "s_click", -26, "profissional", 2, 0.2)
    ev(k["cert2"] - 0.04, "s_click", -26, "escalável", 2, 0.2)
    ev(k["cert3"] - 0.04, "s_click", -26, "stack de ponta", 2, 0.2)
    ev(k["cert_seal"] + 0.22, "stamp", -16, "selo em relevo")
    ev(k["case"] - 0.25, "s_velvet", -20, "troca de plano: o estojo")
    ev(k["case_open"] - 0.22, "s_lock", -20, "estojo abre", 0, 0.4)
    ev(k["case_gem"] + 0.4, "s_crystal", -20, "diamante no nicho", 2)
    ev(k["case_seal"] - 0.08, "s_impact", -15, "selo BLACK NOVEMBER", 1, 1.2)
    ev(k["case_seal"] - 0.05, "s_shimmer", -27, "brilho do selo", 0, 1.6)
    ev(k["forever"] + 0.05, "s_crystal", -22, "infinito", 1)
    ev(k["slam"] - 0.05, "s_slam", -10, "mas atenção: estojo fecha")
    ev(k["slam"] + 0.06, "s_lock", -18, "trava", 0, 0.35)
    ev(k["slam"] + 0.4, "s_velvet", -24, "fita envolve o estojo")
    ev(k["tag"] - 0.1, "s_ticks", -27, "relógio de suspense", 0, 4.5)
    ev(k["flip"] - 0.02, "s_paper", -22, "etiqueta vira", 1, 0.5)
    ev(k["tag_time"] - 0.05, "s_crystal", -26, "19H30", 2)
    ev(k["rope"] - 0.05, "s_velvet", -20, "cordão de veludo entra")
    ev(k["vip_plate"] - 0.05, "s_lock", -22, "plaqueta GRUPO VIP", 1, 0.3)
    ev(k["cta"] - 0.2, "s_velvet", -24, "reorganiza para o CTA")
    ev(k["button"] - 0.1, "s_lift", -22, "botão SAIBA MAIS", 0, 0.5)
    ev(k["button"] + 0.08, "s_click", -18, "toque no botão", 0, 0.2)
    ev(k["rope_open"] - 0.02, "s_lock", -18, "cordão se solta", 1, 0.35)
    ev(k["rope_open"] + 0.05, "s_velvet", -22, "passagem aberta")
    ev(k["toggle"] - 0.02, "s_click", -20, "chave das notificações", 1, 0.15)
    ev(k["toggle"] + 0.08, "s_bell", -26, "sino", 0, 0.9)
    ev(k["envelope"] - 0.03, "s_paper", -20, "envelope desliza", 0, 0.8)
    ev(k["envelope_seal"] - 0.02, "stamp", -22, "lacre", 0)
    ev(k["fin"] - 0.05, "s_crystal", -22, "data da aula", 0)
    ev(k["voice_end"] - 0.1, "s_velvet", -18, "cartão final")
    ev(k["voice_end"] + 0.3, "s_impact", -13, "estojo no centro", 1, 1.4)
    ev(k["voice_end"] + 0.4, "s_shimmer", -24, "brilho do cartão", 0, 2.0)
    ev(k["duration"] - 1.02, "s_crystal", -16, "selo final", 1)
    return sorted(E, key=lambda x: x["time"])


def music_plan(k, music):
    """One driving track that builds under the hook and the steps and drops on the gem flash, silence on the warning
    (slam), the same track filtered under the condition and a second, powerful track for the CTA. The bed is louder
    than the kit default (plan["mix"]): a jewellery commercial needs a score you notice."""
    d = k["duration"]
    m1, m2 = music["main"], music["cta"]
    off = float(music["drop"]) - k["flash"]          # main track time = video time + off (from the spotlight on)
    return [
        {"start": 0.0, "end": k["p0"], "mode": "full", "gain_db": 0, "track": m1, "src": max(0.0, off - 0.5),
         "fade_in": 0.02, "fade_out": 0.02},
        {"start": k["p0"], "end": k["p1"], "mode": "silence"},
        {"start": k["p1"], "end": k["slam"] - 0.05, "mode": "full", "gain_db": 0, "track": m1,
         "src": max(0.0, k["p1"] + off), "fade_in": 0.04, "fade_out": 0.05},
        {"start": k["slam"] - 0.05, "end": k["tag"] - 0.2, "mode": "silence"},
        {"start": k["tag"] - 0.2, "end": k["cta"] - 0.25, "mode": "lowpass", "gain_db": 0, "track": m1,
         "src": max(0.0, k["slam"] + off + 1.0), "fade_in": 0.25, "fade_out": 0.2},
        {"start": k["cta"] - 0.25, "end": d, "mode": "full", "gain_db": 1.0, "track": m2,
         "src": float(music.get("cta_src", 28.0)), "fade_in": 0.15, "fade_out": 1.2},
    ]


def resolve_music(beats, track, drop_s):
    # defaults measured with `heditor music` and the presence band (500 Hz-6 kHz share): music:126 (breakdown 40-48 s,
    # kick enters at 48 s, lands on the gem flash) and Mixkit m179 for the CTA. A bass-only track (presence share ~0.05)
    # reads as "no music" on a phone even at -17 dB.
    m = {"main": "music:126", "drop": 48.0, "cta": "m179", "cta_src": 28.0}
    m.update(beats.get("music", {}))
    if track and Path(track).is_file():          # heditor produce <work> <file|music:ID> <drop>
        m["main"], m["drop"] = track, float(drop_s)
    for key in ("main", "cta"):
        v = str(m[key])
        if v.startswith("music:"):
            m[key] = rk.music_path(v)
        elif not Path(v).is_file():
            m[key] = lk.mixkit(v)
    return m


# ------------------------------------------------------------------ build
def build(track=None, drop_s=0.0):
    beats, T = load_beats()
    rk.setup_assets(WORK)
    glyphs = [p.get("glyph", "code-xml") for p in T["plaques"]]
    rk.ensure_icons(sorted({"code-xml", "mouse-pointer-2", "lock", "bell", "check", "settings", "chevron-down",
                            "pointer", *glyphs}))
    a = WORK / "composition/assets"
    fx, fy = lk.face_median(WORK, rk)                 # median face centre in the source frame (px)
    lk.camera_and_matte(WORK, rk, fx, fy)            # graded plate + presenter matte (rebuilt when stale)
    lk.objects(WORK)                                 # <work>/gen/*.png -> soft-edged object photos
    vm, vr = a / "voice-master.wav", a / "voice-raw.wav"
    if not vm.exists() or vm.stat().st_mtime < vr.stat().st_mtime:
        rk.prepare_voice(WORK)
    words, voice_end, edl = load()
    for w in words:   # uppercase captions: no trailing punctuation inside the pill
        w["shown"] = w["shown"].rstrip(".,;:…") or w["shown"]
    k = keys(words, voice_end, beats)
    if not edl.get("pauses"):
        raise SystemExit('lapidacao: declare the blackout in prepare.py, e.g. ("PAUSE", 0.5, "p_apagao") after the hook')
    pause = edl["pauses"][0]
    k["p0"], k["p1"] = round(pause["out_start"], 4), round(pause["out_end"], 4)
    caps = rk.captions(words, voice_end, max_words=3, max_chars=17)
    music = resolve_music(beats, track, drop_s)
    kjs = dict(k)
    kjs["seed"] = SEED
    kjs["rig"] = beats.get("rig_states") or lk.rig_states(fx, fy)
    kjs["spotx"] = SPOT_X
    kjs["junctions"] = [round(c["out_start"], 3) for c in edl["chunks"] if c["out_start"] > 0.05 and not c.get("pause")]
    kjs["text"] = {"step1": T["step1"], "step2": T["step2"], "floor0": T["floor0"]}
    kjs["floor"] = [[k[key] if key in k else float(key), word] for key, word in beats.get("floor", [])]
    (WORK / "composition/index.html").write_text(page(k, caps, kjs, T))
    plan = {
        "duration": k["duration"], "voice_end": voice_end, "max_duration": float(beats.get("max_duration", 100)),
        "keys": {kk: v for kk, v in k.items() if isinstance(v, (int, float))},
        "captions": caps, "sound_events": sound_events(k), "music": music_plan(k, music),
        "music_ref": [k["p1"], k["slam"]], "cta_boost_db": 3,
        # "presence" profile (rk.MIX_PROFILES) with the targets of the approved reference edit: a score you notice,
        # SFX a little under the profile default; asr-check medium is required by the profile
        "mix": {"profile": "presence", "music_median_db": -15.5, "bed_p95_db": -9.0, "within_10db_pct": 9,
                "low_duck": 0.38, "sfx_duck": 0.7, "sfx_offset_db": -7.0},
        "duck_open": [[k["p0"], k["p1"]]],
        "allowed_numbers": [str(x) for x in beats.get("allowed_numbers", ["01", "02", "03", "04", "05"])],
        "cta": {"kind": "learn_more", "text": T["button"] + " ›"},
        "style": "lapidacao",
    }
    (WORK / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    (WORK / "captions.json").write_text(json.dumps(caps, ensure_ascii=False, indent=2))
    return plan


if __name__ == "__main__":
    p = build()
    print(json.dumps({"duration": p["duration"], "captions": len(p["captions"]), "events": len(p["sound_events"])}))
