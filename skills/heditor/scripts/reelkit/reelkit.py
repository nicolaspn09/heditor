"""reelkit: shared building blocks for heditor compositions.

Each cut defines its own plan (key moments, scenes, sounds, music and CTA) in a `build.py`
and uses this module for captions, the HyperFrames page skeleton, GSAP helpers, the
voice-first mix, camera preparation and face tracking.

Paths are resolved from HEDITOR_HOME (default ~/.heditor), filled by `scripts/setup.sh`.
Brand (name, handle, colours, logo) comes from <work>/brand.json or HEDITOR_HOME/brand.json.
"""

import html
import json
import os
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
HOME = Path(os.environ.get("HEDITOR_HOME", "~/.heditor")).expanduser()
ASSETS = HOME / "assets"
ICON_SRC = ASSETS / "icons"
FONTS = ASSETS / "fonts"
MODELS = ASSETS / "models"
CATALOG = Path(__file__).resolve().parents[2] / "assets/catalog.json"
DEFAULT_BRAND = {
    "name": "Your Brand", "handle": "@yourhandle", "logo": None,
    "colors": {"bg": "#050a14", "bg2": "#081626", "accent": "#edc580", "accent2": "#7dd3fc",
               "alert": "#ff3d57", "ok": "#7dffb0"},
    "follow": "Follow", "following": "Following", "comment": "Comment below", "lang": "pt",
}
# Words that should not end a caption group when the next one follows quickly (pt + en).
FUNCTION_WORDS = {"the", "a", "an", "of", "to", "and", "in", "on", "for", "with", "your", "my", "e", "de", "do", "da", "a", "o", "que", "um", "no", "na", "para", "pra",
                  "pro", "das", "dos", "seu", "sua", "com", "em", "se", "as", "os"}


# ---------------------------------------------------------------- palavras

def load_audio_16k(path, start=None, duration=None):
    """Decode any audio/video with ffmpeg to mono float32 at 16 kHz (avoids PyAV version issues)."""
    import subprocess
    import numpy as np
    args = ["ffmpeg", "-v", "error"]
    if start is not None:
        args += ["-ss", str(start)]
    if duration is not None:
        args += ["-t", str(duration)]
    args += ["-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(args, capture_output=True, check=True).stdout, np.float32).copy()


def load_brand(work=None):
    """Brand settings: <work>/brand.json overrides HEDITOR_HOME/brand.json overrides defaults.

    Long-form CTA words (subscribe, subscribed, watch_next) default to the brand language when absent."""
    brand = json.loads(json.dumps(DEFAULT_BRAND))
    for path in [HOME / "brand.json"] + ([Path(work) / "brand.json"] if work else []):
        if path.exists():
            data = json.loads(path.read_text())
            colors = data.pop("colors", {})
            brand.update(data)
            brand["colors"].update(colors)
    for key, value in LONG_CTA_WORDS.get(brand.get("lang", "en"), LONG_CTA_WORDS["en"]).items():
        brand.setdefault(key, value)
    return brand


LONG_CTA_WORDS = {
    "pt": {"subscribe": "Inscrever-se", "subscribed": "Inscrito", "watch_next": "Assista o próximo"},
    "en": {"subscribe": "Subscribe", "subscribed": "Subscribed", "watch_next": "Watch next"},
    "es": {"subscribe": "Suscribirse", "subscribed": "Suscrito", "watch_next": "Mira el siguiente"},
}


def load_words(path, censor=None):
    raw = json.loads(Path(path).read_text())
    items = raw if isinstance(raw, list) else raw.get("words", [])
    words = []
    for w in items:
        text = w["word"].strip()
        shown = (censor or {}).get(plain(text), None)
        if shown:
            # keep the trailing punctuation of the original token
            tail = re.findall(r"[.,?!:;]+$", text)
            shown = shown + (tail[0] if tail else "")
        words.append({"word": text, "shown": shown or text,
                      "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)})
    words.sort(key=lambda x: x["start"])
    return words


def plain(word):
    return word.strip(".,?!:;").lower()


def finder(words):
    def find(token, after=0.0):
        for w in words:
            if w["start"] >= after - 1e-6 and plain(w["word"]) == token:
                return round(w["start"], 3)
        raise KeyError((token, after))
    return find


def captions(words, voice_end, max_words=3, max_chars=17):
    groups, current = [], []
    for word in words:
        text = word["shown"]
        chars = sum(len(w["shown"]) + 1 for w in current) + len(text)
        gap = word["start"] - current[-1]["end"] if current else 0
        if current and (len(current) >= max_words or chars > max_chars or gap > 0.55):
            groups.append(current)
            current = []
        current.append(word)
        if text.endswith((".", "?", ",", "!")):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    for i, group in enumerate(groups[:-1]):
        nxt = groups[i + 1]
        while len(group) > 1 and plain(group[-1]["word"]) in FUNCTION_WORDS and nxt[0]["start"] - group[-1]["end"] < 0.3:
            nxt.insert(0, group.pop())
    merged = []
    for group in groups:
        if merged:
            prev = merged[-1]
            span = prev[-1]["end"] - prev[0]["start"]
            gap = group[0]["start"] - prev[-1]["end"]
            chars = len(" ".join(w["shown"] for w in prev + group))
            tail = " ".join(w["shown"] for w in group)
            short_tail = len(group) <= 2 and len(tail) <= 7
            ends = prev[-1]["shown"].endswith((".", "?", "!"))
            if (span < 0.42 or short_tail) and gap < 0.30 and chars <= 26 and not ends:
                prev.extend(group)
                continue
        merged.append(list(group))
    out = []
    for i, ws in enumerate(merged):
        start = max(0.0, ws[0]["start"] - 0.04)
        end = min(voice_end, ws[-1]["end"] + 0.10)
        if i + 1 < len(merged):
            end = min(end, merged[i + 1][0]["start"] - 0.04)
        if end <= start:
            end = start + 0.05
        out.append({"id": f"cap-{i}", "start": round(start, 4), "end": round(end, 4),
                    "text": " ".join(w["shown"] for w in ws), "words": ws})
    return out


# ---------------------------------------------------------------- assets

def icon(name, cls="ic"):
    svg = (ICON_SRC / f"{name}.svg").read_text().strip()
    if "-->" in svg:
        svg = svg.split("-->")[-1].strip()
    return svg.replace("<svg", f'<svg class="{cls}"', 1)


def ensure_icons(names):
    ICON_SRC.mkdir(parents=True, exist_ok=True)
    for n in names:
        p = ICON_SRC / f"{n}.svg"
        if not p.exists():
            subprocess.run(["curl", "-sfL", "-o", str(p),
                            f"https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{n}.svg"], check=True)


GSAP_PLUGINS = {  # file stem in ~/.heditor/assets/js/gsap -> global to register (None: registers itself)
    "SplitText": "SplitText", "DrawSVGPlugin": "DrawSVGPlugin", "MorphSVGPlugin": "MorphSVGPlugin",
    "MotionPathPlugin": "MotionPathPlugin", "CustomEase": "CustomEase", "CustomWiggle": "CustomWiggle",
    "CustomBounce": "CustomBounce", "TextPlugin": "TextPlugin", "Physics2DPlugin": "Physics2DPlugin",
    "PhysicsPropsPlugin": "PhysicsPropsPlugin", "ScrambleTextPlugin": "ScrambleTextPlugin", "EasePack": None,
}
GSAP_ALIASES = {"DrawSVG": "DrawSVGPlugin", "MorphSVG": "MorphSVGPlugin", "MotionPath": "MotionPathPlugin",
                "Text": "TextPlugin", "Physics2D": "Physics2DPlugin", "PhysicsProps": "PhysicsPropsPlugin",
                "ScrambleText": "ScrambleTextPlugin"}


def gsap_plugin_tags(names):
    """<script> tags + registerPlugin for GSAP plugins copied by setup_assets (offline, after gsap.min.js).
    CustomWiggle needs CustomEase; it is added automatically. See references/gsap-craft.md for the seek-safe rules."""
    stems = []
    for n in names:
        stem = GSAP_ALIASES.get(n, n)
        if stem not in GSAP_PLUGINS:
            raise ValueError(f"unknown GSAP plugin {n!r}; known: {', '.join(GSAP_PLUGINS)}")
        if stem in ("CustomWiggle", "CustomBounce") and "CustomEase" not in stems:
            stems.append("CustomEase")
        if stem not in stems:
            stems.append(stem)
    if not stems:
        return ""
    tags = "".join(f'<script src="assets/gsap/{s}.min.js"></script>' for s in stems)
    regs = [GSAP_PLUGINS[s] for s in stems if GSAP_PLUGINS[s]]
    return tags + (f"<script>gsap.registerPlugin({','.join(regs)});</script>" if regs else "")


def setup_assets(work):
    """Copy fonts, GSAP (+ plugins), grain, licences and the brand logo into <work>/composition/assets."""
    a = Path(work) / "composition/assets"
    a.mkdir(parents=True, exist_ok=True)
    for src in list(FONTS.glob("*")) + [ASSETS / "js/gsap.min.js", ASSETS / "grain.png", ASSETS / "licenses/Lucide-LICENSE.txt"]:
        if src.is_file() and not (a / src.name).exists():
            (a / src.name).write_bytes(src.read_bytes())
    plugin_dir = ASSETS / "js/gsap"
    if plugin_dir.exists():
        (a / "gsap").mkdir(exist_ok=True)
        for src in plugin_dir.glob("*.min.js"):
            if not (a / "gsap" / src.name).exists():
                (a / "gsap" / src.name).write_bytes(src.read_bytes())
    brand = load_brand(work)
    logo = Path(brand["logo"]).expanduser() if brand.get("logo") else ASSETS / "logo-placeholder.png"
    if logo.exists() and not (a / "logo.png").exists():
        if logo.suffix.lower() == ".png":
            (a / "logo.png").write_bytes(logo.read_bytes())
        else:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(logo), str(a / "logo.png")], check=True)
    return a


def _stale(out, src):
    """Derived media must be rebuilt when missing or older than its source (e.g. after a new EDL).

    Reusing a camera variant made from a previous camera-src.mp4 silently desynchronises picture and voice.
    """
    out, src = Path(out), Path(src)
    return not out.exists() or (src.exists() and out.stat().st_mtime < src.stat().st_mtime)


def prepare_camera(work, width=960):
    a = Path(work) / "composition/assets"
    src = a / "camera-src.mp4"
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", str(src)],
                                   capture_output=True, text=True, check=True).stdout.strip().split(",")[:2])
    height = round(width * h / w / 2) * 2
    out = a / "camera-hd.mp4"
    if _stale(out, src):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf",
                        f"scale={width}:{height}:flags=lanczos,unsharp=5:5:0.55:5:5:0,eq=contrast=1.04:saturation=1.06,format=yuv420p",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-an", str(out)],
                       check=True, timeout=900)
    return width, height


def styled_camera(work, name, vf):
    a = Path(work) / "composition/assets"
    out = a / f"camera-{name}.mp4"
    if _stale(out, a / "camera-hd.mp4"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a / "camera-hd.mp4"), "-vf", vf + ",format=yuv420p",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-an", str(out)], check=True, timeout=900)
    return out.name


# ---------------------------------------------------------------- HTML/CSS/JS

BASE_CSS = r"""
@font-face{font-family:Anton;src:url('assets/Anton-Regular.ttf');font-display:block}
@font-face{font-family:VT;src:url('assets/VT323-Regular.ttf');font-display:block}
@font-face{font-family:Geist;src:url('assets/Geist-VF.ttf');font-weight:100 900;font-display:block}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden;background:var(--bg);color:#f4f8fb;font-family:Geist,sans-serif}
#stage{position:relative;width:1080px;height:1920px;overflow:hidden;background:var(--bg)}
.clip{position:absolute}
.ic{width:48px;height:48px;stroke-width:2;flex:none}
#world{position:absolute;inset:0}
#bg{position:absolute;inset:0;background:radial-gradient(ellipse 80% 55% at 50% 32%,#10304a 0%,var(--bg2) 45%,var(--bg) 78%)}
.layer{position:absolute;inset:0;opacity:0}
.glow{position:absolute;border-radius:50%}
#glow-a{left:-260px;top:120px;width:760px;height:760px;background:radial-gradient(circle,rgba(125,211,252,.18),rgba(125,211,252,0) 65%)}
#glow-b{left:560px;top:900px;width:820px;height:820px;background:radial-gradient(circle,rgba(237,197,128,.15),rgba(237,197,128,0) 65%)}
.floor{position:absolute;left:-540px;top:1180px;width:2160px;height:1300px;transform:perspective(620px) rotateX(68deg);transform-origin:50% 0;background-size:120px 120px}
#floor-a{background-image:linear-gradient(rgba(125,211,252,.20) 2px,transparent 2px),linear-gradient(90deg,rgba(125,211,252,.20) 2px,transparent 2px)}
#horizon{position:absolute;left:0;top:1170px;width:1080px;height:6px;background:linear-gradient(90deg,transparent,var(--accent2),transparent);opacity:.55}
.speed{position:absolute;height:6px;width:520px;border-radius:6px;background:linear-gradient(90deg,transparent,var(--accent2) 40%,#fff);opacity:0}
#rig-aura{position:absolute;left:0;top:0;transform-origin:0 0;z-index:9}
#aura{position:absolute;inset:-40px;border-radius:84px;background:radial-gradient(ellipse at 50% 50%,rgba(237,197,128,.55),rgba(125,211,252,.2) 55%,transparent 72%);opacity:0}
#rig{position:absolute;left:0;top:0;transform-origin:0 0;z-index:10}
#squeeze{position:absolute;inset:0;transform-origin:50% 60%}
#frame{position:absolute;inset:0;border-radius:44px;overflow:hidden;background:#000;box-shadow:0 34px 90px rgba(0,0,0,.65)}
#border{position:absolute;inset:0;border-radius:44px;border:5px solid var(--accent);box-shadow:inset 0 0 0 2px rgba(5,10,20,.5),0 0 0px 2px rgba(125,211,252,.35);pointer-events:none}
#cam-zoom,#cam-breath,#cam-jump{position:absolute;inset:0}
#cam-zoom video{position:absolute;left:0;top:0;object-fit:cover}
#cam-tint{position:absolute;inset:0;background:linear-gradient(180deg,rgba(5,10,20,0) 60%,rgba(5,10,20,.45));pointer-events:none}
#cam-scan{position:absolute;inset:0;opacity:0;background:repeating-linear-gradient(0deg,rgba(0,0,0,.28) 0 2px,transparent 2px 6px)}
.hook{position:absolute;left:0;top:300px;width:1080px;text-align:center;z-index:12;font-family:Anton;line-height:1.02;text-shadow:0 10px 30px rgba(0,0,0,.6)}
.hook .h1{font-size:88px;color:#fff;letter-spacing:1px}
.hook .h2{font-size:112px;color:#fff}
.hook em{display:inline-block;font-style:normal;color:var(--accent)}
.panel{position:absolute;left:90px;width:900px;border-radius:36px;opacity:0;z-index:8}
.caption{left:70px;top:1222px;width:940px;height:250px;z-index:30;display:flex;align-items:center;justify-content:center}
.cap{width:940px;text-align:center;font-family:Anton;font-size:96px;line-height:1.06;text-transform:uppercase;letter-spacing:1px;color:#fff;-webkit-text-stroke:8px var(--bg);paint-order:stroke fill;text-shadow:0 6px 18px rgba(0,0,0,.6);opacity:0;visibility:hidden;text-wrap:balance}
.cap .w{display:inline-block;opacity:.86;transform-origin:50% 70%;margin:0 .06em}
.cap.long{font-size:84px}
.cap.pill .w{border-radius:.14em;padding:0 .1em}
#grain{position:absolute;left:-256px;top:-256px;width:1592px;height:2432px;background:url('assets/grain.png');opacity:.07;z-index:40;pointer-events:none;mix-blend-mode:overlay}
#flash{position:absolute;inset:0;background:#fff;opacity:0;z-index:45;pointer-events:none}
#vignette{position:absolute;inset:0;z-index:19;opacity:0;background:radial-gradient(ellipse at 50% 45%,transparent 45%,rgba(255,40,70,.55))}
.conf{position:absolute;left:540px;top:900px;width:18px;height:30px;border-radius:4px;opacity:0;z-index:21}
.cta-q{position:absolute;left:60px;top:300px;width:960px;text-align:center;z-index:14}
.cta-q .q1{font-family:Anton;font-size:150px;line-height:1;color:var(--accent);opacity:0}
.cta-q .q2{font-family:Anton;font-size:88px;line-height:1.04;margin-top:14px;opacity:0;text-wrap:balance}
.cta-q .q3{display:flex;justify-content:center;align-items:center;gap:16px;margin-top:24px;font-size:42px;color:#cfe0ee;opacity:0}
.cta-q .q3 .ic{width:50px;height:50px;color:var(--accent2)}
#finger{position:absolute;width:110px;height:110px;color:#fff;opacity:0;filter:drop-shadow(0 8px 14px rgba(0,0,0,.6));z-index:30}
#finger .ic{width:110px;height:110px;stroke-width:1.8;fill:rgba(8,22,38,.85)}
#ripple{position:absolute;width:80px;height:80px;border-radius:50%;border:6px solid #fff;opacity:0;z-index:29}
"""

BASE_JS = r"""
const tl=gsap.timeline({paused:true});
const K=window.K;const D=K.duration;
const E={immediateRender:false};
const S=(s,v,t)=>tl.set(s,v,t);
const TO=(s,v,t)=>tl.to(s,v,t);
const FT=(s,a,b,t)=>tl.fromTo(s,a,Object.assign({},E,b),t);
let seed=K.seed||20261012;function rnd(){seed=(seed*1664525+1013904223)%4294967296;return seed/4294967296;}
function scramble(sel,text,t,dur,chars,fps){chars=chars||'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&*<>/';fps=fps||15;const n=Math.max(2,Math.round(dur*fps)),fr=[];for(let i=0;i<=n;i++){const k=Math.floor(text.length*i/n);let s=text.slice(0,k);for(let j=k;j<text.length;j++)s+=/\s/.test(text[j])?text[j]:chars[Math.floor(rnd()*chars.length)];fr.push(s);}fr[n]=text;const el=document.querySelector(sel);if(el)el.textContent=fr[0];const o={p:0};tl.fromTo(o,{p:0},{p:1,duration:dur,ease:'none',immediateRender:false,onUpdate:()=>{if(el)el.textContent=fr[Math.min(n,Math.floor(o.p*n+1e-6))];}},t);}
const RIG=K.rigStates;
gsap.set('#rig',RIG.hero);gsap.set('#rig-aura',RIG.hero);gsap.set('#world',{x:0,y:0});gsap.set('#cam-zoom',{scale:1});gsap.set('#flash',{opacity:0});
TO('#glow-a',{x:180,y:260,duration:D,ease:'sine.inOut'},0);
TO('#glow-b',{x:-220,y:-300,duration:D,ease:'sine.inOut'},0);
TO('#grain',{x:256,y:256,duration:D,ease:'steps('+Math.round(D*15)+')'},0);
function rig(state,t,d){const v=Object.assign({duration:d||.5,ease:'expo.inOut'},RIG[state]);TO('#rig',v,t);TO('#rig-aura',Object.assign({},v),t);}
function shake(t,a){[[a,-a*.6],[-a*.8,a*.5],[a*.5,a*.4],[-a*.3,-a*.3],[0,0]].forEach((p,i)=>TO('#world',{x:p[0],y:p[1],duration:.035,ease:'power1.inOut'},t+i*.035));}
function flash(t,p,d,color){S('#flash',{backgroundColor:color||'#ffffff'},t-.001);FT('#flash',{opacity:p},{opacity:0,duration:d||.22,ease:'power2.out'},t);}
function punch(t,s,hold,back){TO('#cam-zoom',{scale:s,duration:.13,ease:'power4.out'},t-.04);TO('#cam-zoom',{scale:back||1,duration:.42,ease:'power3.inOut'},t+hold);}
function pop(sel,t,from){FT(sel,Object.assign({opacity:0,scale:.4},from||{}),{opacity:1,scale:1,x:0,y:0,rotation:0,duration:.28,ease:'back.out(2.2)'},t);}
function out(sel,t,v){TO(sel,Object.assign({opacity:0,duration:.22,ease:'power2.in'},v||{}),t);}
function confetti(t,cx,cy){document.querySelectorAll('.conf').forEach((el)=>{const a=rnd()*Math.PI*2,r=240+rnd()*380;const dx=Math.cos(a)*r,dy=Math.sin(a)*r-200;
  S(el,{left:cx,top:cy,opacity:1,x:0,y:0,rotation:0},t);TO(el,{x:dx,y:dy,rotation:rnd()*720-360,duration:.55,ease:'power3.out'},t);TO(el,{y:dy+700,opacity:0,duration:.9,ease:'power1.in'},t+.56);});}
function speedlines(t){document.querySelectorAll('.speed').forEach((el,i)=>{FT(el,{opacity:0,x:1200},{opacity:.9,x:-1300,duration:.45,ease:'power2.in'},t+i*.05);});}
K.rig.forEach((r,i)=>{if(i)rig(r[1],r[0],r[2]);});
// Pause cuts: alternate zoom 1.0/1.075 per segment (the jump reads as a new shot), centred on the median
// face position of the segment, with a slow 1.5% breathing zoom inside each segment.
if(K.segments){K.segments.forEach((sg,i)=>{const o=sg.x+'% '+sg.y+'%';
  S(['#cam-jump','#cam-breath','#cam-zoom'],{transformOrigin:o},sg.start);
  S('#cam-jump',{scale:(i%2?1.075:1)},sg.start);
  FT('#cam-breath',{scale:1},{scale:1.015,duration:Math.max(.2,sg.end-sg.start),ease:'sine.inOut'},sg.start);});}
"""


def captions_js(caps, gold="#f5c66b", mode="text", pill=("#000000", "#ffd84d")):
    """mode="text": active word in gold; mode="pill": active word as pure black text on a light-yellow pill.

    Dark text with a dark outline on a mid-tone pill reads poorly on phones; in pill mode the outline takes
    the pill colour so the black letters stay crisp."""
    if mode == "pill":
        fg, bg = pill
        r, g, b = (int(bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        on = f'{{opacity:1,color:"{fg}",backgroundColor:"{bg}",webkitTextStrokeColor:"{bg}",scale:1.06}}'
        off = f'{{color:"#ffffff",backgroundColor:"rgba({r},{g},{b},0)",webkitTextStrokeColor:"#050a14",scale:1}}'
    else:
        on = f'{{opacity:1,color:"{gold}",scale:1.08}}'
        off = '{color:"#ffffff",scale:1}'
    out = []
    for cap in caps:
        c = f'#{cap["id"]}-c'
        out.append(f'tl.set("{c}",{{visibility:"visible",opacity:1}},{cap["start"]:.4f});')
        out.append(f'tl.fromTo("{c}",{{scale:.86,y:16}},{{scale:1,y:0,duration:.12,ease:"back.out(2.5)",immediateRender:false}},{cap["start"]:.4f});')
        for j, w in enumerate(cap["words"]):
            wid = f'#{cap["id"]}-w{j}'
            t = max(cap["start"], w["start"] - 0.02)
            out.append(f'tl.set("{wid}",{on},{t:.4f});')
            if j + 1 < len(cap["words"]):
                nxt = cap["words"][j + 1]["start"] - 0.02
                if nxt > t:
                    out.append(f'tl.set("{wid}",{off},{nxt:.4f});')
        out.append(f'tl.set("{c}",{{visibility:"hidden",opacity:0}},{cap["end"]:.4f});')
    return "".join(out)


def captions_html(caps, track=50):
    out = []
    for cap in caps:
        words = " ".join(f'<span id="{cap["id"]}-w{j}" class="w">{html.escape(w["shown"])}</span>'
                         for j, w in enumerate(cap["words"]))
        long = " long" if len(cap["text"]) > 18 else ""
        out.append(f'<div id="{cap["id"]}" class="clip caption" data-start="{cap["start"]:.4f}" '
                   f'data-duration="{cap["end"] - cap["start"]:.4f}" data-track-index="{track}">'
                   f'<div id="{cap["id"]}-c" class="cap{long}">{words}</div></div>')
    return "".join(out)


# Reels top safe margin: 14% of 1920 px (Meta guidance for 9:16 Reels: keep text, faces, logos
# and key graphics below the top 14%).
SAFE_TOP = 270
# The fixed caption band starts at 1222 px; the hero camera card ends before it.
CARD_BOTTOM_MAX = 1200
PANEL_TOP_MIN = 670


def rig_states(card_w, card_h, hero_y=500, top_scale=0.5, top_y=SAFE_TOP + 10):
    """Camera card states: hero below the top text, top inside the safe area."""
    hero_scale = min(1.0, (CARD_BOTTOM_MAX - hero_y) / card_h)
    return {
        "hero": {"x": (1080 - card_w * hero_scale) / 2, "y": hero_y, "scale": round(hero_scale, 4)},
        "top": {"x": (1080 - card_w * top_scale) / 2, "y": top_y, "scale": top_scale},
    }


def page(*, title, duration, card_w, card_h, face_origin, videos, scenes_html, css, js, keys, caps,
         world_back="", overlays="", caption_mode="text", brand_work=None, fmt=None, plugins=(),
         caption_pill=("#000000", "#ffd84d")):
    """Reel page skeleton. `fmt` (formats key, default 9:16) only changes the canvas size: the Reel layout
    (caption band, rig states) is vertical; long-form/horizontal compositions use longkit.
    `plugins`: GSAP plugins to load offline and register, e.g. ("SplitText", "DrawSVG", "MorphSVG").
    `caption_pill`: (text, pill) colours of the active word in pill mode (hex, keep >= 4.5:1)."""
    import formats
    canvas = formats.get(fmt)
    brand = load_brand(brand_work)
    c = brand["colors"]
    conf_colors = [c["accent"], c["accent2"], "#ffffff", "#ff5fa2", c["ok"]]
    conf = "".join(f'<div class="conf" style="background:{conf_colors[i % 5]}"></div>' for i in range(40))
    speed = "".join(f'<div class="speed" style="top:{180 + i * 110}px;left:{(i * 137) % 400}px"></div>'
                    for i in range(10))
    vids = "".join(
        f'<video id="{v["id"]}" class="clip" data-start="{v["start"]:.4f}" '
        + (f'data-media-start="{v["media_start"]:.4f}" ' if v.get("media_start") else "")
        + f'data-duration="{v["duration"]:.4f}" data-track-index="{v["track"]}" src="assets/{v["src"]}" '
        f'style="width:{card_w}px;height:{card_h}px" muted playsinline></video>'
        for v in videos)
    root = ":root{" + "".join(f"--{k}:{v};" for k, v in c.items()) + "}"
    size_css = "" if canvas.key == "9:16" else f"html,body,#stage{{width:{canvas.width}px;height:{canvas.height}px}}"
    extra_css = (root + size_css + f"#rig,#rig-aura{{width:{card_w}px;height:{card_h}px}}"
                 f"#cam-zoom,#cam-breath,#cam-jump{{transform-origin:{face_origin}}}")
    return f"""<!doctype html><html lang="{brand.get('lang', 'pt')}"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<script src="assets/gsap.min.js"></script>{gsap_plugin_tags(plugins)}<style>{BASE_CSS}{extra_css}{css}</style></head><body>
<main id="stage" data-composition-id="main" data-start="0" data-duration="{duration:.4f}" data-width="{canvas.width}" data-height="{canvas.height}" data-fps="30">
<div id="world">
<div id="bg"></div>{world_back}<div class="glow" id="glow-a"></div><div class="glow" id="glow-b"></div>
<div class="floor" id="floor-a"></div><div id="horizon"></div>{speed}
<div id="rig-aura"><div id="aura"></div></div>
<div id="rig"><div id="squeeze"><div id="frame"><div id="cam-zoom"><div id="cam-breath"><div id="cam-jump">{vids}</div></div></div><div id="cam-tint"></div><div id="cam-scan"></div><div id="cam-over"></div></div><div id="border"></div></div></div>
{scenes_html}
{overlays}
<div id="vignette"></div>{conf}
</div>
{captions_html(caps)}
<div id="grain"></div><div id="flash"></div>
<audio id="master" class="clip" data-start="0" data-duration="{duration:.4f}" data-track-index="100" src="assets/master.wav" data-volume="1"></audio>
</main>
<script>window.K={json.dumps(keys, ensure_ascii=False)};window.captionData={json.dumps(caps, ensure_ascii=False)};</script>
<script>{BASE_JS}{js}{captions_js(caps, mode=caption_mode, pill=caption_pill)}window.__timelines=window.__timelines||{{}};window.__timelines.main=tl;</script>
</body></html>"""


# ---------------------------------------------------------------- audio

VOICE_CHAIN = ("adeclip=threshold=1,highpass=f=85,afftdn=nr=12:nf=-40:tn=1,"
               "equalizer=f=250:t=q:w=1.2:g=-2.5,equalizer=f=3200:t=q:w=1.0:g=2.5,deesser=i=0.3,"
               "acompressor=threshold=-22dB:ratio=3:attack=8:release=150:makeup=2,alimiter=limit=0.9:level=false")


def prepare_voice(work):
    a = Path(work) / "composition/assets"
    out = a / "voice-master.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a / "voice-raw.wav"), "-af", VOICE_CHAIN,
                    "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(out)], check=True, timeout=300)
    return out


def decode(path, start=0.0, duration=None, filters=None):
    args = ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, start):.4f}"]
    if duration:
        args += ["-t", f"{duration:.4f}"]
    args += ["-i", str(path)]
    if filters:
        args += ["-af", filters]
    args += ["-ac", "2", "-ar", str(SR), "-f", "f32le", "pipe:1"]
    raw = subprocess.run(args, capture_output=True, check=True, timeout=180).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def ramp(x, fi=0.005, fo=0.03):
    n = len(x)
    a, b = min(n, round(fi * SR)), min(n, round(fo * SR))
    if a:
        x[:a] *= np.linspace(0, 1, a)[:, None]
    if b:
        x[-b:] *= np.linspace(1, 0, b)[:, None]
    return x


def db(v):
    return 10 ** (v / 20)


def voice_envelope(voice, n):
    hop = 480
    pad = np.pad(voice, (0, (-len(voice)) % hop))
    rms = np.sqrt(np.mean(pad.reshape(-1, hop) ** 2, axis=1))
    active = np.clip((20 * np.log10(rms + 1e-9) + 46) / 10, 0, 1)
    look, hold = 12, 65
    held = np.array([active[max(0, i - hold): i + look + 1].max() for i in range(len(active))])
    out = np.zeros_like(held)
    level = 0.0
    for i, v in enumerate(held):
        level += (v - level) * (0.35 if v > level else 0.06)
        out[i] = level
    return np.interp(np.arange(n), np.arange(len(out)) * hop, out, right=0)


MUSIC_FILTERS = {
    "full": None,
    "lowpass": "lowpass=f=700,lowpass=f=700,volume=2.2",
    "vhs": "highpass=f=180,lowpass=f=2800,vibrato=f=3.5:d=0.12,volume=1.6",
    "retro": "highpass=f=250,lowpass=f=3200,acrusher=bits=8:mode=log:aa=1:mix=0.6,volume=1.6",
    "radio": "highpass=f=400,lowpass=f=3000,volume=2.0",
    "muffled": "lowpass=f=400,volume=2.4",
}


def loudnorm_two_pass(src, dst, target=-14.0, tp=-2.0, lra=9.0):
    """Two-pass loudnorm: measure, then apply the measured values (linear when possible)."""
    first = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                            f"loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=180).stderr
    m = json.loads(first[first.rindex("{"): first.rindex("}") + 1])
    af = (f"loudnorm=I={target}:TP={tp}:LRA={lra}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", str(SR), "-ac", "2",
                    "-c:a", "pcm_s16le", str(dst)], check=True, timeout=180)
    return m


def track_faces(work, video="camera-hd.mp4", step=0.2):
    """Face centre (fraction of width/height) every `step` seconds, using MediaPipe."""
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    path = Path(work) / "composition/assets" / video
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", str(path)],
                                   capture_output=True, text=True, check=True).stdout.strip().split(",")[:2])
    # Detect on a downscaled copy: positions are fractions, and 5 fps of full-HD RGB frames
    # (~6 MB each) exhausts the memory of a small VPS on cuts longer than ~40 s.
    if w > 640:
        w, h = 640, max(2, round(h * 640 / w / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={1 / step},scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=str(MODELS / "blaze_face_short_range.tflite")),
        min_detection_confidence=0.4))
    out = []
    for i, f in enumerate(frames):
        r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(f)))
        if r.detections:
            b = max(r.detections, key=lambda d: d.categories[0].score).bounding_box
            out.append({"t": round(i * step, 3), "x": (b.origin_x + b.width / 2) / w, "y": (b.origin_y + b.height / 2) / h})
    det.close()
    (Path(work) / "qa/face-track.json").write_text(json.dumps(out, indent=1))
    return out


def jump_segments(work, faces, voice_end, default=(0.45, 0.5)):
    """Segments between EDL cuts with the median face centre of each one (never smoothed across a cut)."""
    edl = json.loads((Path(work) / "edl.json").read_text())
    cuts = sorted({round(c["out_start"], 3) for c in edl["chunks"]} | {0.0})
    segs = []
    for i, a in enumerate(cuts):
        b = cuts[i + 1] if i + 1 < len(cuts) else voice_end
        pts = [f for f in faces if a <= f["t"] < b]
        x = float(np.median([p["x"] for p in pts])) if pts else default[0]
        y = float(np.median([p["y"] for p in pts])) if pts else default[1]
        segs.append({"start": a, "end": b, "x": round(x * 100, 1), "y": round(y * 100, 1)})
    return segs


# Mix profiles (plan["mix"] = "voice" | "presence" | {"profile": ..., <overrides>}).
#   voice    — organic Reels, class excerpts, dense explanations: music ~21.5 dB under the voice.
#   presence — paid ads and creative mode: a rhythmic bed that is felt the whole time (~15 dB under the voice,
#              the values of the approved trailer), filtered sections get make-up gain, asr-check is mandatory.
# Both have a presence floor: the bed's presence band (500 Hz-6 kHz, after ducking: what the ear hears as "the
# track" over a voice) may not stay under voice median + presence_floor_db for longer than presence_gap_s inside
# the speech, outside sections the plan declares as "silence". Calibrated on a real case: a 16 s muffled section and
# a quiet intro read as "no music" at -44..-58 dB; a bed that read as present sat at -28..-36 dB.
MIX_PROFILES = {
    "voice": {"music_median_db": -21.5, "bed_p95_db": -12.0, "within_10db_pct": 5, "music_duck": 0.80,
              "low_duck": 0.55, "sfx_duck": 0.85, "sfx_offset_db": -7.0, "filtered_makeup_db": 0.0,
              "presence_floor_db": -48.0, "presence_gap_s": 8.0, "asr_check_required": False},
    "presence": {"music_median_db": -15.0, "bed_p95_db": -7.0, "within_10db_pct": 30, "music_duck": 0.62,
                 "low_duck": 0.35, "sfx_duck": 0.60, "sfx_offset_db": -4.0, "filtered_makeup_db": 4.0,
                 "presence_floor_db": -38.0, "presence_gap_s": 2.0, "asr_check_required": True},
}
FILTERED_MODES = ("muffled", "lowpass")


def mix_targets(plan):
    """Resolved mix targets of a plan: profile defaults + explicit overrides (legacy dicts keep working)."""
    over = plan.get("mix") or {}
    if isinstance(over, str):
        over = {"profile": over}
    name = over.get("profile") or plan.get("mix_profile") or "voice"
    if name not in MIX_PROFILES:
        raise ValueError(f"unknown mix profile {name!r}; use one of {sorted(MIX_PROFILES)}")
    targets = dict(MIX_PROFILES[name])
    targets.update({k: v for k, v in over.items() if k != "profile"})
    targets["profile"] = name if not (set(over) - {"profile"}) else f"{name}+custom"
    return targets


def presence_levels(x, hop, lo=500.0, hi=6000.0):
    """Per-window level (dB) of the presence band of a mono signal (Hann-windowed FFT power, RMS-equivalent)."""
    f = np.fft.rfftfreq(hop, 1 / SR)
    band = (f >= lo) & (f < hi)
    win = np.hanning(hop)
    out = []
    for i in range(len(x) // hop):
        spec = np.abs(np.fft.rfft(x[i * hop:(i + 1) * hop] * win)) ** 2
        out.append(10 * np.log10(spec[band].sum() * 2 / (hop * np.sum(win ** 2)) + 1e-12))
    return np.array(out)


def music_gaps(levels_db, voice_ref_db, eligible, hop_s, floor_db, min_s=0.8, bridge_s=1.2):
    """Runs of windows where the bed falls under voice_ref + floor (eligible windows only).

    levels_db: per-window presence-band level of the bed (presence_levels); eligible: bool per window (inside the
    speech, outside declared silence). Runs separated by less than bridge_s are merged (a bed that only peeks out
    for a moment is still "gone"). Returns [(start_s, end_s)] of runs >= min_s and the % of eligible windows present."""
    rel = np.asarray(levels_db) - voice_ref_db
    low = np.asarray(eligible) & (rel < floor_db)
    gaps, i = [], 0
    while i < len(low):
        if low[i]:
            j = i
            while j < len(low) and low[j]:
                j += 1
            if (j - i) * hop_s >= min(min_s, bridge_s) / 2 - 1e-9:
                gaps.append((round(i * hop_s, 2), round(j * hop_s, 2)))
            i = j
        else:
            i += 1
    merged = []
    for g in gaps:
        if merged and g[0] - merged[-1][1] < bridge_s - 1e-9:
            merged[-1] = (merged[-1][0], g[1])
        else:
            merged.append(g)
    merged = [g for g in merged if g[1] - g[0] >= min_s - 1e-9]
    n = int(np.sum(eligible))
    present = float(np.mean(~low[np.asarray(eligible)]) * 100) if n else 100.0
    return merged, present


def mix(work, plan, sfx_lib, music_body_db=-21.0, music_duck=0.80, sfx_offset_db=-7.0, sfx_duck=0.85,
        multiband=True, low_duck=0.55):
    """Mix with a profile (MIX_PROFILES): "voice" (default, music ~21.5 dB under the voice) or "presence" (paid
    ads, creative mode: ~15 dB under, filtered make-up, asr-check required). plan["mix"] = "presence" or a dict
    {"profile": "presence", <overrides>}; legacy dicts without "profile" override the voice profile. The same
    targets are read by test_voice_first_balance and test_music_presence (rk.mix_targets)."""
    work = Path(work)
    tg = mix_targets(plan)
    music_duck = tg.get("music_duck", music_duck)
    low_duck = tg.get("low_duck", low_duck)
    sfx_duck = tg.get("sfx_duck", sfx_duck)
    sfx_offset_db = tg.get("sfx_offset_db", sfx_offset_db)
    target_med = float(tg["music_median_db"])
    target_p95 = float(tg["bed_p95_db"])
    makeup = float(tg.get("filtered_makeup_db", 0.0))
    a = work / "composition/assets"
    duration = plan["duration"]
    n = round(duration * SR)
    with wave.open(str(a / "voice-master.wav")) as src:
        voice = np.frombuffer(src.readframes(src.getnframes()), "<i2") / 32768.0
    vfull = np.pad(voice, (0, max(0, n - len(voice))))[:n]
    env = voice_envelope(voice, n)
    # Dramatic pauses (style trailer): inside these windows the voice is digital silence, so the ducking is
    # released at once instead of holding ~650 ms; hits, braams and the music swell land at full level.
    for w0, w1 in plan.get("duck_open", []):
        s0, s1 = max(0, round(w0 * SR)), min(n, round(w1 * SR))
        r = min(round(0.03 * SR), max(1, (s1 - s0) // 4))
        if s1 - s0 > 2 * r:
            win = np.ones(s1 - s0)
            win[:r] = np.linspace(0, 1, r)
            win[-r:] = np.linspace(1, 0, r)
            env[s0:s1] *= 1 - win
    music = np.zeros((n, 2))
    music_low = np.zeros((n, 2))
    log = []
    for sec in plan["music"]:
        if sec["mode"] == "silence":
            continue
        start, end = sec["start"], min(sec["end"], duration)
        base = MUSIC_FILTERS[sec["mode"]]
        first = round(start * SR)
        for band, filt in (("low", "lowpass=f=200"), ("high", "highpass=f=200")):
            chain = ",".join(x for x in (base, filt) if x) if multiband else base
            seg = decode(sec["track"], sec["src"], end - start + 0.05, chain)
            seg = ramp(seg[: round((end - start) * SR)], sec.get("fade_in", 0.012), sec.get("fade_out", 0.025))
            if makeup and sec["mode"] in FILTERED_MODES:
                seg = seg * db(makeup)
            target = music_low if (multiband and band == "low") else music
            target[first: first + len(seg)] += seg[: n - first]
            if not multiband:
                break
        log.append(dict(sec))
    ref = plan.get("music_ref", [0, duration])
    body = (music + music_low)[round(ref[0] * SR): round(ref[1] * SR)]
    norm = db(music_body_db) / max(np.sqrt(np.mean(body ** 2)), 1e-9)
    music *= norm
    music_low *= norm
    gain = np.ones(n)
    for sec in plan["music"]:
        s0, s1 = round(sec["start"] * SR), min(n, round(sec["end"] * SR))
        gain[s0:s1] = db(sec.get("gain_db", 0))
    if plan.get("cta_boost_db"):
        gain[round((plan["voice_end"] + 0.2) * SR):] *= db(plan["cta_boost_db"])
    sm = round(0.04 * SR)
    gain = np.convolve(np.pad(gain, (sm, sm), mode="edge"), np.ones(sm) / sm, mode="same")[sm:-sm]
    music *= gain[:, None]
    music_low *= gain[:, None]
    # Ducking por faixa: a banda da fala (acima de 200 Hz) desce com music_duck; os graves descem menos,
    # para a trilha continuar presente sem disputar com a voz.
    music *= (1 - music_duck * env)[:, None]
    music_low *= (1 - low_duck * env)[:, None]
    music = music + music_low

    sfx = np.zeros((n, 2))
    cache = {}
    used = []
    for ev in plan["sound_events"]:
        entry = sfx_lib[ev["category"]]
        files = entry["files"]
        rel = files[ev.get("variant", 0) % len(files)]
        rate = ev.get("rate", 1.0)
        key = (rel, rate)
        if key not in cache:
            data = decode(rel)
            if rate != 1.0:
                pos = np.arange(0, len(data) - 1, rate)
                data = np.column_stack([np.interp(pos, np.arange(len(data)), data[:, c]) for c in (0, 1)])
            cache[key] = data
        data = cache[key].copy()
        mode, length = entry.get("trim", ("head", 0.6))
        length = ev.get("length", length)
        data = data[-round(length * SR):] if mode == "tail" else data[: round(length * SR)]
        data = ramp(data, 0.004, 0.04)
        data = data / (np.max(np.abs(data)) or 1.0) * db(ev["gain_db"] + 3 + sfx_offset_db)
        first = max(0, round(ev["time"] * SR))
        last = min(n, first + len(data))
        sfx[first:last] += data[: last - first]
        used.append(dict(ev, file=str(rel)))
    sfx *= (1 - sfx_duck * env)[:, None]

    hop = 19200
    m = (n // hop) * hop

    def lv(x):
        return 20 * np.log10(np.sqrt(np.mean(x[:m].reshape(-1, hop) ** 2, axis=1)) + 1e-9)

    vr = lv(vfull)
    # effective speech windows: within 15 dB of the loudest window (pauses and tails excluded)
    vo = vr > (vr.max() - 15)
    # auto-calibration to the profile targets (voice: music ~21.5 dB under, p95 >= 12 dB under; presence: -15/-7)
    for _ in range(4):
        mr = lv(music.mean(1))
        br = lv((music + sfx).mean(1))
        med = float(np.median(mr[vo] - vr[vo]))
        p95 = float(np.percentile(br[vo] - vr[vo], 95))
        adj = min(target_med - med, target_p95 - p95, 0.0) if (med > target_med or p95 > target_p95) else 0.0
        if abs(adj) < 0.2:
            break
        music *= db(adj)
    mr, sr_, br = lv(music.mean(1)), lv(sfx.mean(1)), lv((music + sfx).mean(1))
    rel = br[vo] - vr[vo]
    balance = {"bed_minus_voice_median_db": float(np.median(rel)), "bed_minus_voice_p95_db": float(np.percentile(rel, 95)),
               "music_minus_voice_median_db": float(np.median(mr[vo] - vr[vo])),
               "sfx_minus_voice_p95_db": float(np.percentile(sr_[vo] - vr[vo], 95)),
               "windows_bed_within_10db_pct": float(np.mean(rel > -10) * 100), "windows": int(vo.sum())}
    # presence floor: the bed may not vanish inside the speech (outside declared silence / no-music plans)
    hop_s = hop / SR
    tracked = [sec for sec in plan["music"] if sec["mode"] != "silence" and sec.get("track")]
    elig = np.zeros(len(vr), bool)
    for w in range(len(vr)):
        t0, t1 = w * hop_s, (w + 1) * hop_s
        if t1 > plan["voice_end"] + 1e-6:
            break
        inside = any(sec["start"] <= t0 + 1e-6 and t1 <= min(sec["end"], duration) + 1e-6 for sec in tracked)
        elig[w] = inside
    hi_db = presence_levels(music.mean(1), hop)
    gaps, present = music_gaps(hi_db, float(np.median(vr[vo])), elig, hop_s, float(tg["presence_floor_db"]))
    long_filtered = [[sec["start"], sec["end"], sec["mode"]] for sec in plan["music"]
                     if sec["mode"] in FILTERED_MODES and sec["end"] - sec["start"] > 3.0]
    balance.update({"mix_profile": tg["profile"], "music_presence_pct": round(present, 1),
                    "music_gaps": [list(g) for g in gaps], "presence_floor_db": tg["presence_floor_db"],
                    "presence_gap_s": tg["presence_gap_s"], "long_filtered_sections": long_filtered,
                    "asr_check_required": bool(tg.get("asr_check_required"))})
    mixd = music + sfx + np.column_stack([vfull] * 2)
    peak = float(np.max(np.abs(mixd)))
    if peak > 0.89:
        mixd *= 0.89 / peak

    def write(name, arr, ch=2):
        with wave.open(str(a / name), "wb") as o:
            o.setnchannels(ch)
            o.setsampwidth(2)
            o.setframerate(SR)
            o.writeframes((np.clip(arr, -1, 1) * 32767).astype("<i2").tobytes())

    write("premaster.wav", mixd)
    write("music-bed.wav", music)
    write("sound-design.wav", sfx)
    loudnorm_two_pass(a / "premaster.wav", a / "master.wav")
    (work / "sound-events.json").write_text(json.dumps(used, ensure_ascii=False, indent=2))
    (work / "music-sections.json").write_text(json.dumps(log, ensure_ascii=False, indent=2, default=str))
    (work / "qa/balance.json").write_text(json.dumps(balance, indent=2))
    return balance


def sfx_library():
    """SFX by category from the heditor catalog; files live in HEDITOR_HOME/assets/sfx (downloaded by setup)."""
    cat = json.loads(CATALOG.read_text())
    lib = {}
    for name, items in cat["sfx"].items():
        files = [str(ASSETS / "sfx" / f"{name}-{it['id']}{Path(it['url']).suffix}") for it in items]
        files = [f for f in files if Path(f).exists()]
        if files:
            lib[name] = {"files": files, "trim": tuple(items[0]["trim"])}
    return lib


def music_path(music_id):
    """Local path of a catalog track (music:<id>)."""
    return str(ASSETS / "music" / f"music-{int(str(music_id).split(':')[-1])}.mp3")
