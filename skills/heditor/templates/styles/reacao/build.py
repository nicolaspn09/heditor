"""Style `reacao`: the speaker reacts in front of the post/news. Runs as-is once beats.json exists; make it yours by
rewriting beats.json from the speech (format below) and, if the video needs it, the scenes.

The speaker is cut out (matte) and placed at the bottom of the frame, in front of the subject he is talking about:
a post, a news article, a repository, a launch page, a screen recording. The subject fills the frame behind him and
lives with the speech: it is pushed in, scrolled and panned to the part being discussed, boxes/markers/circles are
drawn on its words, the source changes on the sentence that brings it. A highlighter headline opens the video, cards
name the subject, captions run over the chest. Recipe and rules: references/styles/reacao.md.

    heditor new <work> <video> --style reacao          # scaffolds this file, prepare.py and DESIGN.md
    # prepare.py: BLOCKS and the CROP of the speaker; heditor prepare; heditor words (fix names in words-reviewed)
    # backdrops: heditor capture <url> <work>/gen/post.png | a screenshot from the user | heditor region (the post
    #            inside the raw recording: split-screen, screen share) | an external screen recording
    # write <work>/beats.json (format below), then:
    heditor produce <work> reacao 0                    # music: beats.json "music" or the style default

beats.json = {"sources": {...}, "shots": [...], "marks": [...], "hook": {...}, "titles": [...], "punches": [...],
              "cta": {...}, "music": {...}, "caption_y": 1508, "credit_hold": 2.8, "speaker_states": {...}, "matte_classes": [1, 2, 3, 4, 5],
              "allowed_numbers": [...], "max_duration": 75}
  times  every "at"/"until" is [spoken token, after_seconds] (token without punctuation, accents must match; "after"
         disambiguates repeats) or a number of seconds of the cut
  sources {name: {"kind": "image", "src": "gen/post.png"}            screenshot / full-page capture (static or scrolled)
                 | {"kind": "region", "crop": "crop=w:h:x:y", "vf": ""}  a region of the raw recording, same EDL
                 | {"kind": "clip", "src": "gen/rec.mp4", "media_start": 0} an external clip (plays from its first shot)
          + "credit": "site.com" (small source chip; write what the viewer must know: site, profile, date as spoken)}
  credits [[T, "fal.ai"], [T, "fal.live"], ...]  optional timed chips (one region that shows several sites); each chip
         shows for credit_hold seconds after its source arrives (top right), then leaves the top to cards and marks
  shots  [{"at": T, "source": name, "focus": [cx, cy, w], "speaker": "center|right|left|small|low|hero|punch",
           "enter": "cut|swipe|flash|zoom", "drift": 0.03, "anchor_y": 760, "min_bottom": 1300, "max_top": 0,
           "moves": [{"at": T, "focus": [cx, cy, w], "dur": 0.9, "ease": "power2.inOut", "anchor_y": 760}],
           "speaker_moves": [[T, "state"], ...]}]
         focus = the point of the backdrop (source px) shown at (540, anchor_y) with w source px across the frame;
         the backdrop always covers the width and the top and reaches min_bottom (default 1300, the speaker's head;
         per shot or move): a landscape recording is zoomed at least to that height, w is a wish; max_top > 0
         lets it start lower (the 0-270 band becomes atmosphere) to bring its first lines under the platform UI;
         scroll = a move that changes cy, push-in = smaller w. drift = slow push-in while a focus holds.
         enter on a shot of the same source: "flash" marks a new page inside it (a recording that navigates).
  marks  [{"at": T, "until": T, "source": name, "kind": "box|marker|underline|circle", "rect": [x, y, w, h],
           "label": "words from the speech", "color": "#ffd84d"}]   rect in source px of that backdrop
  hook   {"lines": ["HEADLINE LINE 1", "LINE 2"], "until": T, "y": 352}   highlighter headline from frame 0 (what
         is said); move it down (y ≤ 960) when the subject's own title sits under it
  titles [{"at": T, "until": T, "kicker": "LANÇAMENTO", "title": "Name <em>accent</em>"}]   top card naming the subject
  punches [[token, after, scale, hold_s], ...]                 hard punch-in on the speaker
  speaker_states {"name": [size, face_x, face_y]}              add/override states (reacaokit.SPEAKER_STATES)
  cta    {"line": "...", "kind": "follow" | "none", "speaker": "center"}   4 s profile card after the speech (Follow ->
         Following) above the frozen last frame of the speaker (moved to the "speaker" state);
         "none" ends with the speech (the speaker already said the CTA)
  music  {"main": "music:187" | "m<mixkit id>" | path, "drop": 0.0, "gain_db": 0}   drop = track second at t = 0
Every number on screen must be spoken (or listed in allowed_numbers with the reason in DESIGN.md).
"""
import html
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("HEDITOR_KIT", str(Path.home() / ".heditor/kit")))
import reacaokit as rx  # noqa: E402
import reelkit as rk  # noqa: E402

WORK = Path(__file__).resolve().parent
CTA = 4.0
SEED = 20261022
DEFAULT_MUSIC = "music:187"
ENTER_DUR = {"cut": 0.0, "flash": 0.0, "swipe": 0.34, "zoom": 0.3}


# ------------------------------------------------------------------ inputs
def load_beats():
    p = WORK / "beats.json"
    if not p.exists():
        raise SystemExit(f"reacao: write {p} from the speech first (format at the top of build.py)")
    b = json.loads(p.read_text())
    for f in ("sources", "shots"):
        if not b.get(f):
            raise SystemExit(f"reacao: beats.json needs '{f}'")
    return b


def load():
    f = WORK / "words-reviewed.json" if (WORK / "words-reviewed.json").exists() else WORK / "words.json"
    words = rk.load_words(f)
    edl = json.loads((WORK / "edl.json").read_text())
    return words, round(edl["voice_duration"], 3), edl


def timer(words, voice_end):
    find = rk.finder(words)

    def at(spec, default=None):
        if spec is None:
            return default
        if isinstance(spec, (int, float)):
            t = float(spec)
        else:
            tok, after = spec[0], float(spec[1]) if len(spec) > 1 else 0.0
            try:
                t = find(rk.plain(tok), after)
            except KeyError:
                t = None
            if t is None:
                near = [round(w["start"], 2) for w in words if rk.plain(w["word"]) == rk.plain(tok)]
                raise SystemExit(f"reacao: token {spec!r} not found after {after} s (it is spoken at {near})")
        return round(min(max(0.0, t), voice_end), 4)
    return at


# ------------------------------------------------------------------ sources
def prepare_sources(b):
    out = {}
    for i, (name, s) in enumerate(b["sources"].items()):
        kind = s.get("kind", "image")
        if kind == "region":
            asset = rx.region_clip(WORK, name, s["crop"], s.get("vf", ""))
        elif kind == "clip":
            asset = rx.external_clip(WORK, name, WORK / s["src"], s.get("vf", ""))
        elif kind == "image":
            asset = rx.image_backdrop(WORK, name, WORK / s["src"])
        else:
            raise SystemExit(f"reacao: unknown source kind {kind!r}")
        w, h, dur = rx.probe(WORK / "composition/assets" / asset)
        fill = rx.fill_layer(WORK, name, "image" if kind == "image" else "video")
        last = rx.last_frame(WORK, name) if kind != "image" else None
        out[name] = {"name": name, "kind": kind, "asset": asset, "fill": fill, "w": w, "h": h, "dur": dur, "last": last,
                     "credit": s.get("credit", ""), "media_start": float(s.get("media_start", 0.0)), "idx": i}
    return out


def timeline(b, at, src, voice_end, states):
    """Shots -> per-source transform events, source switches, speaker events."""
    shots = []
    for s in b["shots"]:
        shots.append(dict(s, t=at(s.get("at", 0.0), 0.0)))
    shots.sort(key=lambda s: s["t"])
    shots[0]["t"] = 0.0
    moves, switches, spk, used = [], [], [], {}
    for i, s in enumerate(shots):
        name = s["source"]
        if name not in src:
            raise SystemExit(f"reacao: shot uses unknown source {name!r}")
        S = src[name]
        t0 = s["t"]
        t1 = shots[i + 1]["t"] if i + 1 < len(shots) else voice_end + CTA
        anchor = float(s.get("anchor_y", 760))
        drift = float(s.get("drift", 0.03))
        floor, ceil = float(s.get("min_bottom", 1300)), float(s.get("max_top", 0))
        keyf = [(t0, s["focus"], 0.0, "none", anchor, floor, ceil)]
        for m in s.get("moves", []):
            keyf.append((at(m["at"]), m["focus"], float(m.get("dur", 0.9)), m.get("ease", "power2.inOut"),
                         float(m.get("anchor_y", anchor)), float(m.get("min_bottom", floor)),
                         float(m.get("max_top", ceil))))
        keyf.sort(key=lambda k: k[0])
        for j, (t, focus, dur, ease, anchor, floor, ceil) in enumerate(keyf):
            x, y, sc = rx.view(S["w"], S["h"], focus, anchor, min_bottom=floor, max_top=ceil)
            moves.append({"sel": f"#c-{name}", "t": t, "dur": dur, "x": x, "y": y, "s": sc, "ease": ease})
            hold0 = t + dur
            hold1 = keyf[j + 1][0] if j + 1 < len(keyf) else t1
            if drift > 0 and hold1 - hold0 > 0.6:
                k = drift * min(1.0, (hold1 - hold0) / 6.0)
                fx, fy, fw = (float(v) for v in focus[:3])
                x2, y2, s2 = rx.view(S["w"], S["h"], [fx, fy, fw * (1 - k)], anchor, min_bottom=floor, max_top=ceil)
                moves.append({"sel": f"#c-{name}", "t": hold0, "dur": round(hold1 - hold0, 4), "x": x2, "y": y2,
                              "s": s2, "ease": "none"})
        prev = shots[i - 1]["source"] if i else None
        if prev != name:
            switches.append({"t": t0, "show": name, "hide": prev, "enter": s.get("enter", "cut" if i == 0 else "swipe")})
        elif s.get("enter") == "flash" and t0 > 0.05:   # same source, new page inside it (a recording that navigates)
            switches.append({"t": t0, "show": name, "hide": None, "enter": "flash"})
        state = s.get("speaker")
        if state:
            spk.append({"t": t0, "state": state, "dur": 0.0})
        for t_spec, st in s.get("speaker_moves", []):
            spk.append({"t": at(t_spec), "state": st, "dur": 0.0})
        used.setdefault(name, []).append((t0, t1))
    for e in spk:
        if e["state"] not in states:
            raise SystemExit(f"reacao: unknown speaker state {e['state']!r} (states: {sorted(states)})")
    if not spk or spk[0]["t"] > 0:
        spk.insert(0, {"t": 0.0, "state": "center", "dur": 0.0})
    return shots, moves, switches, sorted(spk, key=lambda e: e["t"]), used


def scale_at(moves, sel, t):
    s = None
    for m in sorted(moves, key=lambda m: m["t"]):
        if m["sel"] == sel and m["t"] <= t + 1e-6:
            s = m["s"]
    return s or 1.0


# ------------------------------------------------------------------ captions
def caption_html(caps):
    out = []
    for c in caps:
        n = len(c["text"])
        fs = int(min(72, 820 / (0.62 * max(n, 7))))
        words = " ".join(f'<span id="{c["id"]}-w{j}" class="w">{html.escape(w["shown"])}</span>'
                         for j, w in enumerate(c["words"]))
        out.append(f'<div id="{c["id"]}" class="clip caption" data-start="{c["start"]:.4f}" '
                   f'data-duration="{c["end"] - c["start"]:.4f}" data-track-index="50">'
                   f'<div id="{c["id"]}-c" class="cap" style="font-size:{fs}px">{words}</div></div>')
    return "".join(out)


# ------------------------------------------------------------------ page
CSS = r"""
@font-face{font-family:Geist;src:url('assets/Geist-VF.ttf');font-weight:100 900;font-display:block}
@font-face{font-family:Inter;src:url('assets/Inter-VF.ttf');font-weight:100 900;font-display:block}
html,body{margin:0;background:#000}
#stage{position:relative;width:1080px;height:1920px;overflow:hidden;background:#0b0b0f;font-family:Geist,Inter,sans-serif}
#bd{position:absolute;inset:0;overflow:hidden}
.src{position:absolute;inset:0;visibility:hidden;transform-origin:50% 50%}
.fill{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover}
.cam{position:absolute;left:0;top:0;transform-origin:0 0}
.media{position:absolute;left:0;top:0;width:100%;height:100%;display:block;
  -webkit-mask-image:linear-gradient(180deg,#000 0,#000 calc(100% - 160px),transparent);mask-image:linear-gradient(180deg,#000 0,#000 calc(100% - 160px),transparent)}
.mark{position:absolute;opacity:0;pointer-events:none}
.mark.box{box-sizing:border-box;border-style:solid;border-color:var(--mc);box-shadow:0 0 0 2px rgba(0,0,0,.35),0 0 32px var(--mc)}
.mark.marker{background:var(--mc);opacity:0;mix-blend-mode:multiply;transform-origin:0 50%}
.mark.marker.screen{mix-blend-mode:screen}
.mark.underline .bar{position:absolute;left:0;right:0;bottom:0;background:var(--mc);transform-origin:0 50%;transform:scaleX(0);box-shadow:0 0 18px var(--mc)}
.mark.circle svg{position:absolute;inset:-6%;width:112%;height:112%;overflow:visible}
.mark.circle ellipse{fill:none;stroke:var(--mc);stroke-linecap:round;filter:drop-shadow(0 0 10px var(--mc))}
.mlabel{position:absolute;left:0;white-space:nowrap;background:var(--mc);color:#0b0b0f;font-family:Geist;font-weight:900;
  border-radius:999px;padding:.18em .6em;letter-spacing:-.01em;box-shadow:0 6px 22px rgba(0,0,0,.45)}
#shade-b{position:absolute;left:0;right:0;bottom:0;height:900px;background:linear-gradient(0deg,rgba(5,6,10,.96),rgba(5,6,10,.78) 25%,rgba(5,6,10,.36) 58%,rgba(5,6,10,0))}
#shade-t{position:absolute;left:0;right:0;top:0;height:520px;background:linear-gradient(180deg,rgba(0,0,0,.48),rgba(0,0,0,0))}
.credit{position:absolute;right:54px;top:280px;display:flex;align-items:center;gap:12px;font-family:Inter;font-weight:700;font-size:26px;
  color:#fff;background:rgba(11,11,15,.72);border:1px solid rgba(255,255,255,.18);border-radius:999px;padding:9px 20px 9px 14px;opacity:0}
.credit i{width:12px;height:12px;border-radius:50%;background:#ff3b30;box-shadow:0 0 12px #ff3b30;display:inline-block}
#spk{position:absolute;left:0;top:0;transform-origin:0 0}
#spk-punch{position:relative;-webkit-mask-image:linear-gradient(180deg,#000 0,#000 80%,transparent 100%);mask-image:linear-gradient(180deg,#000 0,#000 80%,transparent 100%)}
#spk-glow{position:absolute;pointer-events:none;background:radial-gradient(ellipse at 50% 55%,rgba(0,0,0,.58),rgba(0,0,0,.28) 42%,rgba(0,0,0,0) 68%)}
#alpha,#spk-last{position:absolute;left:0;top:0;width:100%;height:100%}
#spk-last{opacity:0}
#hook{position:absolute;left:60px;right:60px;top:var(--hooky);text-align:center;opacity:0}
#hook .hl{display:inline;font-family:Geist;font-weight:900;font-size:var(--hfs,68px);line-height:1.32;color:#0b0b0f;background:var(--hl);
  padding:.06em .28em;border-radius:14px;-webkit-box-decoration-break:clone;box-decoration-break:clone;letter-spacing:-.02em}
#hook .ln{display:block;margin:0 0 6px}
.title{position:absolute;left:60px;right:60px;top:var(--ty,346px);background:#fff;color:#0b0b0f;border-radius:30px;padding:26px 34px 30px;
  box-shadow:0 22px 60px rgba(0,0,0,.45);opacity:0}
.title .k{font-family:Inter;font-weight:800;font-size:28px;letter-spacing:.16em;text-transform:uppercase;color:var(--ac)}
.title .t{font-family:Geist;font-weight:900;font-size:58px;line-height:1.04;letter-spacing:-.03em;margin-top:8px;text-wrap:balance}
.title .t em{font-style:normal;color:var(--ac)}
.caption{position:absolute;left:0;top:0;width:1080px;height:1920px;pointer-events:none}
.cap{position:absolute;left:50px;right:50px;top:var(--capy);text-align:center;visibility:hidden;font-family:Geist;font-weight:900;
  line-height:1.08;color:#fff;letter-spacing:-.01em;-webkit-text-stroke:12px #000;paint-order:stroke fill;
  text-shadow:0 6px 20px rgba(0,0,0,.6)}
.cap .w{display:inline-block;margin:0 .1em}
#cta{position:absolute;inset:0;opacity:0}
#cta-dim{position:absolute;inset:0;background:linear-gradient(180deg,rgba(6,7,10,.62),rgba(6,7,10,.45) 55%,rgba(6,7,10,.2))}
#cta-card{position:absolute;left:110px;right:110px;top:300px;background:rgba(16,18,24,.94);border:1px solid rgba(255,255,255,.16);border-radius:40px;
  padding:40px 40px 44px;text-align:center;box-shadow:0 30px 90px rgba(0,0,0,.6)}
#cta-card img{width:140px;height:140px;border-radius:50%;object-fit:cover;border:5px solid var(--ac);background:#000}
#cta-card .n{font-family:Geist;font-weight:900;font-size:60px;color:#fff;margin-top:18px}
#cta-card .h{font-family:Inter;font-weight:700;font-size:34px;color:#9aa3b2;margin-top:4px}
#cta-card .l{font-family:Inter;font-weight:700;font-size:38px;line-height:1.28;color:#e9edf3;margin:26px auto 0;max-width:760px}
#cta-btn{position:relative;display:inline-block;margin-top:34px;width:440px;height:104px;border-radius:999px;background:var(--ac);
  font-family:Geist;font-weight:900;font-size:44px;line-height:104px;color:#fff}
#cta-btn span{position:absolute;inset:0}
#cta-btn .b2{opacity:0;color:#0b0b0f}
#flash{position:absolute;inset:0;background:#fff;opacity:0;pointer-events:none}
"""


def page(k, caps, src, marks, titles, hook, T, states, cam_w, cam_h, face):
    E = html.escape
    tracks = iter(range(2, 49))
    layers = []
    for name, S in src.items():
        if S["kind"] == "image":
            fill = f'<img id="if-{name}" class="fill" src="assets/{S["fill"]}">'
            media = f'<img id="im-{name}" class="media" src="assets/{S["asset"]}">'
        else:
            start = 0.0 if S["kind"] == "region" else T["first_use"][name]
            dur = (k["voice_end"] if S["kind"] == "region"
                   else max(0.1, min(k["duration"] - start, (S["dur"] or 999) - S["media_start"])))
            ms = "" if S["kind"] == "region" else f' data-media-start="{S["media_start"]:.4f}"'
            fill = (f'<video id="vf-{name}" class="fill clip" data-start="{start:.4f}" data-duration="{dur:.4f}"{ms} '
                    f'data-track-index="{next(tracks)}" src="assets/{S["fill"]}" muted playsinline></video>')
            media = (f'<img id="il-{name}" class="media" src="assets/{S["last"]}">'
                     f'<video id="vm-{name}" class="media clip" data-start="{start:.4f}" data-duration="{dur:.4f}"{ms} '
                     f'data-track-index="{next(tracks)}" src="assets/{S["asset"]}" muted playsinline></video>')
        mk = "".join(m["html"] for m in marks if m["source"] == name)
        layers.append(f'<div class="src" id="s-{name}">{fill}<div class="cam" id="c-{name}" '
                      f'style="width:{S["w"]}px;height:{S["h"]}px">{media}{mk}</div></div>')
    hook_html = ""
    if hook:
        fs = int(min(68, 930 / (0.55 * max(len(x) for x in hook["lines"]))))
        hook_html = f'<div id="hook" style="--hfs:{fs}px">' + "".join(f'<span class="ln"><span class="hl">{E(x)}</span></span>'
                                                 for x in hook["lines"]) + "</div>"
    titles_html = "".join(f'<div class="title" id="ti{i}"' + (f' style="--ty:{int(t["y"])}px"' if t.get("y") else "")
                          + f'><div class="k">{E(t["kicker"])}</div>'
                          f'<div class="t">{t["title"]}</div></div>' for i, t in enumerate(titles))
    credits_html = "".join(f'<div class="credit" id="cr-{n}"><i></i><span>{E(text)}</span></div>'
                           for n, text in T["credit_texts"].items())
    gx, gy = face
    glow = (f'<div id="spk-glow" style="left:{gx - cam_w * 0.62:.0f}px;top:{gy - cam_h * 0.42:.0f}px;'
            f'width:{cam_w * 1.24:.0f}px;height:{cam_h * 1.3:.0f}px"></div>')
    last = (f'<img id="spk-last" src="assets/{T["last"]}">' if T.get("last") else "")
    brand = T["brand"]
    cta_html = ""
    if T["cta_kind"] == "follow":
        cta_html = (f'<div id="cta"><div id="cta-dim"></div><div id="cta-card"><img src="assets/logo.png">'
                    f'<div class="n">{E(brand["name"])}</div><div class="h">{E(brand["handle"])}</div>'
                    f'<div class="l">{E(T["cta_line"])}</div>'
                    f'<div id="cta-btn"><span class="b1">{E(brand["follow"])}</span>'
                    f'<span class="b2">{E(brand["following"])}</span></div></div></div>')
    css_vars = (f':root{{--hl:{T["hl"]};--ac:{T["accent"]};--capy:{T["caption_y"]}px;--hooky:{T["hook_y"]}px}}'
                f'#spk-punch{{width:{cam_w}px;height:{cam_h}px;transform-origin:{gx:.0f}px {cam_h}px}}')
    return f"""<!doctype html><html lang="pt"><head><meta charset="utf-8"><title>reacao</title>
<script src="assets/gsap.min.js"></script><style>{CSS}{css_vars}</style></head><body>
<main id="stage" data-composition-id="main" data-start="0" data-duration="{k['duration']:.4f}" data-width="1080" data-height="1920" data-fps="30">
<div id="bd">{''.join(layers)}</div>
<div id="shade-t"></div><div id="shade-b"></div>
{cta_html}
{credits_html}
<div id="spk"><div id="spk-punch">{glow}
  <video id="alpha" class="clip" data-start="0" data-duration="{k['voice_end']:.4f}" data-track-index="1" src="assets/camera-alpha.webm" muted playsinline></video>{last}
</div></div>
{hook_html}{titles_html}
{caption_html(caps)}
<div id="flash"></div>
<audio id="master" class="clip" data-start="0" data-duration="{k['duration']:.4f}" data-track-index="100" src="assets/master.wav" data-volume="1"></audio>
</main>
<script>window.K={json.dumps(T['K'], ensure_ascii=False)};</script>
<script>{JS}{rk.captions_js(caps, mode="text", gold=T['active'])}window.__timelines=window.__timelines||{{}};window.__timelines.main=tl;</script>
</body></html>"""


JS = r"""
const tl = gsap.timeline({paused:true});
const S=(s,v,t)=>tl.set(s,v,t);
const D=K.duration, V=K.voice_end, ST=K.states;
// backdrop transforms (focus, scroll, drift)
for (const m of K.moves){
  if (m.dur<=0) S(m.sel,{x:m.x,y:m.y,scale:m.s},m.t);
  else tl.to(m.sel,{x:m.x,y:m.y,scale:m.s,duration:m.dur,ease:m.ease},m.t);
}
// source switches
for (const w of K.switches){
  const n='#s-'+w.show, o=w.hide?'#s-'+w.hide:null;
  if (w.enter==='swipe' && o){
    tl.fromTo(n,{y:1920,autoAlpha:1},{y:0,duration:.34,ease:'power3.out',immediateRender:false},w.t);
    tl.to(o,{y:-520,autoAlpha:0,duration:.34,ease:'power3.out'},w.t);
    S(o,{y:0},w.t+.36);
  } else if (w.enter==='zoom' && o){
    tl.fromTo(n,{scale:1.14,autoAlpha:0},{scale:1,autoAlpha:1,duration:.3,ease:'power2.out',immediateRender:false},w.t);
    S(o,{autoAlpha:0},w.t+.3);
  } else {
    S(n,{autoAlpha:1,y:0,scale:1},w.t); if (o) S(o,{autoAlpha:0},w.t);
    if (w.enter==='flash' && w.t>0.05) tl.fromTo('#flash',{opacity:.85},{opacity:0,duration:.16,ease:'power1.out',immediateRender:false},w.t);
  }
}
// source credit chip
// the chip names the source for a few seconds after it arrives, then gets out of the way of cards and marks
for (let i=0;i<K.credits.length;i++){
  const c=K.credits[i], nxt=(i+1<K.credits.length)?K.credits[i+1].t:D;
  if (c.hide) S('#cr-'+c.hide,{opacity:0},c.t);
  if (c.show){
    tl.fromTo('#cr-'+c.show,{opacity:0,x:16},{opacity:1,x:0,duration:.25,ease:'power2.out',immediateRender:false},c.t+.05);
    const off=Math.min(c.t+K.credit_hold, nxt-.05);
    if (off>c.t+.4) tl.to('#cr-'+c.show,{opacity:0,duration:.25},off);
  }
}
// speaker states (hard cuts) and punch-ins
for (const e of K.spk){ const st=ST[e.state]; if (e.dur>0) tl.to('#spk',{x:st.x,y:st.y,scale:st.s,duration:e.dur,ease:'expo.out'},e.t); else S('#spk',{x:st.x,y:st.y,scale:st.s},e.t); }
for (const p of K.punches){ S('#spk-punch',{scale:p[1]},p[0]); tl.to('#spk-punch',{scale:1,duration:.18,ease:'power2.out'},p[0]+p[2]); }
// marks
for (const m of K.marks){
  const s='#'+m.id;
  if (m.kind==='box') tl.fromTo(s,{opacity:0,scale:.9},{opacity:1,scale:1,duration:.24,ease:'back.out(2.2)',immediateRender:false},m.t);
  else if (m.kind==='marker') tl.fromTo(s,{opacity:.62,scaleX:0},{opacity:.62,scaleX:1,duration:.34,ease:'power2.out',immediateRender:false},m.t);
  else if (m.kind==='underline'){ S(s,{opacity:1},m.t); tl.fromTo(s+' .bar',{scaleX:0},{scaleX:1,duration:.32,ease:'power2.out',immediateRender:false},m.t); }
  else if (m.kind==='circle'){ S(s,{opacity:1},m.t); tl.fromTo(s+' ellipse',{strokeDashoffset:m.len},{strokeDashoffset:0,duration:.5,ease:'power2.inOut',immediateRender:false},m.t); }
  if (m.label) tl.fromTo(s+' .mlabel',{opacity:0,y:10},{opacity:1,y:0,duration:.2,ease:'power2.out',immediateRender:false},m.t+.12);
  tl.to(s,{opacity:0,duration:.2},m.until);
}
// hook headline (visible on frame 0)
if (K.hook){
  S('#hook',{opacity:1},0);
  tl.fromTo('#hook .ln',{scale:.86,y:12},{scale:1,y:0,duration:.22,stagger:.07,ease:'back.out(2)',immediateRender:true},0);
  tl.to('#hook',{opacity:0,y:-18,duration:.2},K.hook.until);
}
for (const t of K.titles){
  tl.fromTo('#'+t.id,{opacity:0,y:-22},{opacity:1,y:0,duration:.26,ease:'power3.out',immediateRender:false},t.t);
  tl.to('#'+t.id,{opacity:0,y:-18,duration:.2},t.until);
}
// end: the speaker freezes on the last frame, the profile card comes in
if (document.getElementById('spk-last')) S('#spk-last',{opacity:1},Math.max(0,V-1/30));
if (document.getElementById('cta')){
  { const st=ST[K.cta_speaker]; if (st) S('#spk',{x:st.x,y:st.y,scale:st.s},V); }
  tl.fromTo('#cta',{opacity:0},{opacity:1,duration:.3,ease:'power1.out',immediateRender:false},V);
  tl.fromTo('#cta-card',{y:60,scale:.94},{y:0,scale:1,duration:.4,ease:'back.out(1.6)',immediateRender:false},V);
  tl.to('#cta-btn',{scale:.92,duration:.09,yoyo:true,repeat:1},V+1.9);
  S('#cta-btn',{backgroundColor:'#ffffff'},V+2.0); S('#cta-btn .b1',{opacity:0},V+2.0); S('#cta-btn .b2',{opacity:1},V+2.0);
  tl.to('.credit',{opacity:0,duration:.2},V);
}
tl.to({}, {duration:.001}, D-.001);
"""


def transform_at(moves, sel, t):
    """Target transform (x, y, s) of the latest move of `sel` started at or before t (+0.05 s)."""
    cur = None
    for m in sorted(moves, key=lambda m: m["t"]):
        if m["sel"] == sel and m["t"] <= t + 0.05:
            cur = (m["x"], m["y"], m["s"])
    return cur or (0.0, 0.0, 1.0)


def state_at(spk, t):
    cur = spk[0]["state"]
    for e in spk:
        if e["t"] <= t + 0.05:
            cur = e["state"]
    return cur


def marks_qa(marks_js, b, moves, spk, states, head):
    """Screen rect of every mark when it appears, with warnings: outside the frame margins or behind the head."""
    rows = []
    for mj, m in zip(marks_js, b.get("marks", [])):
        tx, ty, s = transform_at(moves, f"#c-{m['source']}", mj["t"])
        x, y, w, h = (float(v) for v in m["rect"])
        r = [round(tx + s * x), round(ty + s * y), round(s * w), round(s * h)]
        st = states[state_at(spk, mj["t"])]
        hx0, hx1 = st["x"] + st["s"] * head["x0"], st["x"] + st["s"] * head["x1"]
        htop = st["y"] + st["s"] * head["top"]
        warn = []
        if r[0] < 24 or r[0] + r[2] > 1056:
            warn.append("touches the frame side")
        if r[1] < 200:
            warn.append("above the safe top (y < 200)")
        if r[1] + r[3] > htop and r[0] < hx1 and r[0] + r[2] > hx0:
            cover = (min(r[1] + r[3], 1920) - max(r[1], htop)) / max(1, r[3])
            if cover > 0.25:
                warn.append(f"{round(cover * 100)}% behind the speaker")
        rows.append({"id": mj["id"], "t": mj["t"], "kind": mj["kind"], "screen": r, "state": state_at(spk, mj["t"]),
                     "warnings": warn})
    (WORK / "qa").mkdir(exist_ok=True)
    (WORK / "qa/marks.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    for r in rows:
        if r["warnings"]:
            print(f"reacao QA: mark {r['id']} at {r['t']:.2f}s {r['screen']}: {'; '.join(r['warnings'])}")
    return rows


def build_marks(b, at, src, moves):
    out, js = [], []
    for i, m in enumerate(b.get("marks", [])):
        name = m["source"]
        t, until = at(m["at"]), at(m.get("until"), None)
        until = until if until and until > t else t + 2.5
        tx, _, sc = transform_at(moves, f"#c-{name}", t)
        x, y, w, h = (float(v) for v in m["rect"])
        kind = m.get("kind", "box")
        color = m.get("color", "#ffd84d")
        bw = 7 / sc
        mid = f"mk{i}"
        style = f"left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;height:{h:.0f}px;--mc:{color};"
        inner, extra = "", {}
        if kind == "box":
            style += f"border-width:{bw:.1f}px;border-radius:{16 / sc:.1f}px;"
        elif kind == "marker":
            style += f"border-radius:{6 / sc:.1f}px;"
        elif kind == "underline":
            inner = f'<div class="bar" style="height:{10 / sc:.1f}px;bottom:{-14 / sc:.1f}px;border-radius:{5 / sc:.1f}px"></div>'
        elif kind == "circle":
            import math
            rx_, ry_ = w / 2, h / 2
            per = round(math.pi * (3 * (rx_ + ry_) - math.sqrt((3 * rx_ + ry_) * (rx_ + 3 * ry_))) * 1.12, 1)
            inner = (f'<svg viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none"><ellipse cx="{w / 2:.0f}" '
                     f'cy="{h / 2:.0f}" rx="{w / 2:.0f}" ry="{h / 2:.0f}" stroke-width="{bw:.1f}" '
                     f'stroke-dasharray="{per}" stroke-dashoffset="{per}" transform="rotate(-3 {w / 2:.0f} {h / 2:.0f})"/></svg>')
            extra["len"] = per
        label = m.get("label", "")
        if label:
            fs = 34 / sc
            side = m.get("label_side", "top")
            pos = f"top:{-fs * 1.9:.0f}px" if side == "top" else f"top:{h + fs * 0.7:.0f}px"
            left_px = tx + sc * x                    # keep the pill at least 40 px inside the frame
            est_w = sc * fs * (0.62 * len(label) + 1.2)
            shift = max(0.0, 40 - left_px) + min(0.0, 1040 - (max(left_px, 40) + est_w))
            pos += f";left:{shift / sc:.0f}px"
            inner += f'<div class="mlabel" style="font-size:{fs:.1f}px;{pos}">{html.escape(label)}</div>'
        cls = kind + (" screen" if m.get("blend") == "screen" else "")
        out.append({"source": name, "html": f'<div class="mark {cls}" id="{mid}" style="{style}">{inner}</div>'})
        js.append(dict({"id": mid, "kind": kind, "t": t, "until": until, "label": bool(label)}, **extra))
    return out, js


# ------------------------------------------------------------------ sound and music
def resolve_music(b, track, drop_s):
    m = b.get("music", {})
    main = track if track and track not in ("reacao", "default", "") else m.get("main", DEFAULT_MUSIC)
    if isinstance(main, str) and (main.startswith("music:") or main.startswith("m") and main[1:].isdigit()):
        main = rk.music_path(main if main.startswith("music:") else "music:" + main[1:])
    drop = float(m.get("drop", drop_s or 0.0))
    return main, drop


def sound_events(k, K):
    ev = []

    def add(t, cat, gain, ctx, length=None):
        e = {"time": round(max(0.0, t), 3), "category": cat, "variant": 0, "gain_db": gain, "context": ctx}
        if length:
            e["length"] = length
        ev.append(e)

    if K.get("hook"):
        add(0.02, "pop", -24, "headline on frame 0", 0.25)
    for w in K["switches"]:
        if w["t"] > 0.1:
            add(w["t"] - 0.04, "swipe" if w["enter"] == "swipe" else "whoosh", -24, f"backdrop -> {w['show']}", 0.4)
    last = -9
    for m in K["marks"]:
        if m["t"] - last < 0.35:
            continue
        last = m["t"]
        add(m["t"], "pen_write" if m["kind"] in ("circle", "underline", "marker") else "click", -27,
            f"mark {m['kind']}", 0.45 if m["kind"] != "box" else 0.15)
    for t in K["titles"]:
        add(t["t"], "pop", -26, "title card", 0.2)
    for p in K["punches"]:
        add(p[0], "bass_impact", -27, "punch-in", 0.4)
    if K.get("cta_kind") == "follow":
        v = k["voice_end"]
        add(v, "whoosh", -22, "to CTA", 0.5)
        add(v + 1.9, "click", -16, "follow press", 0.2)
        add(v + 2.0, "success_chime", -20, "following", 0.9)
    return sorted(ev, key=lambda e: e["time"])


def music_plan(k, track, drop, gain_db=0.0):
    """One full bed from frame 0 (the reaction starts at full speed); `drop` = second of the track at t = 0. Put the
    track's kick entry on the strongest turn (src = kick_s - word_s, `heditor music`)."""
    return [{"start": 0.0, "end": k["duration"], "mode": "full", "gain_db": gain_db, "track": track, "src": drop,
             "fade_in": 0.3, "fade_out": 1.0}]


# ------------------------------------------------------------------ build
def build(track=None, drop_s=0.0):
    b = load_beats()
    brand = rk.load_brand(WORK)
    rk.setup_assets(WORK)
    cam_w, cam_h = rx.speaker_cutout(WORK, keep=tuple(b.get("matte_classes", (1, 2, 3, 4, 5))))
    vm, vr = WORK / "composition/assets/voice-master.wav", WORK / "composition/assets/voice-raw.wav"
    if not vm.exists() or vm.stat().st_mtime < vr.stat().st_mtime:
        rk.prepare_voice(WORK)
    words, voice_end, edl = load()
    at = timer(words, voice_end)
    faces = rk.track_faces(WORK, video="camera-hd.mp4", step=0.25)
    xs = sorted(f["x"] for f in faces if f.get("x") is not None) or [0.5]
    ys = sorted(f["y"] for f in faces if f.get("y") is not None) or [0.4]
    fx, fy = xs[len(xs) // 2] * cam_w, ys[len(ys) // 2] * cam_h
    states = rx.speaker_states(fx, fy, cam_w, cam_h, {k: tuple(v) for k, v in b.get("speaker_states", {}).items()})
    src = prepare_sources(b)
    shots, moves, switches, spk, used = timeline(b, at, src, voice_end, states)
    k = {"voice_end": voice_end, "duration": round(voice_end + (CTA if b.get("cta", {}).get("kind", "follow") == "follow" else 0.0), 3)}
    marks, marks_js = build_marks(b, at, src, moves)
    top = rx.speaker_top(WORK)
    head = {"top": top * cam_h, "x0": fx - 0.22 * cam_w, "x1": fx + 0.22 * cam_w}
    marks_qa(marks_js, b, moves, spk, states, head)
    hook = b.get("hook")
    titles = [dict(t, id=f"ti{i}", t=at(t["at"]), until=at(t.get("until"), voice_end)) for i, t in enumerate(b.get("titles", []))]
    punches = [[at([p[0], p[1]]), float(p[2]), float(p[3])] for p in b.get("punches", [])]
    credits, credit_texts = [], {}
    if b.get("credits"):   # timed chips, e.g. one region that shows several sites: [[T, "fal.ai"], [T, "fal.live"]]
        prev = None
        for i, (t_spec, text) in enumerate(b["credits"]):
            cid = f"t{i}"
            credit_texts[cid] = text
            credits.append({"t": at(t_spec), "show": cid if text else None, "hide": prev})
            prev = cid if text else None
    else:
        for w in switches:
            credits.append({"t": w["t"], "show": w["show"] if src[w["show"]]["credit"] else None,
                            "hide": w["hide"] if w["hide"] and src[w["hide"]]["credit"] else None})
        credit_texts = {n: S["credit"] for n, S in src.items() if S["credit"]}
    caps = rk.captions(words, voice_end, max_words=3, max_chars=16)
    cta_kind = b.get("cta", {}).get("kind", "follow")
    last = rx.freeze_alpha(WORK) if cta_kind == "follow" else None
    K = {"duration": k["duration"], "voice_end": voice_end, "seed": SEED, "states": states, "moves": moves,
         "switches": switches, "spk": spk, "marks": marks_js, "punches": punches, "credits": credits,
         "hook": ({"until": at(hook.get("until"), 3.0)} if hook else None),
         "titles": [{"id": t["id"], "t": t["t"], "until": t["until"]} for t in titles], "cta_kind": cta_kind,
         "cta_speaker": b.get("cta", {}).get("speaker", "center"), "credit_hold": float(b.get("credit_hold", 2.8))}
    T = {"K": K, "brand": brand, "first_use": {n: min(a for a, _ in v) for n, v in used.items()},
         "hl": b.get("highlight", "#d8ff3e"), "accent": b.get("accent", "#2f6bff"),
         "active": b.get("active", "#ffd84d"), "caption_y": int(b.get("caption_y", 1508)),
         "cta_kind": cta_kind, "cta_line": b.get("cta", {}).get("line", ""), "last": last,
         "credit_texts": credit_texts, "hook_y": int((hook or {}).get("y", 352))}
    (WORK / "composition/index.html").write_text(page(k, caps, src, marks, titles, hook, T, states, cam_w, cam_h, (fx, fy)))
    main, drop = resolve_music(b, track, drop_s)
    keys = {"hook_until": K["hook"]["until"] if hook else 0.0}
    for i, s in enumerate(shots):
        keys[f"shot{i}"] = s["t"]
    for m in marks_js:
        keys[m["id"]] = m["t"]
    plan = {
        "style": "reacao", "duration": k["duration"], "voice_end": voice_end,
        "max_duration": float(b.get("max_duration", 75)), "keys": keys, "captions": caps,
        "sound_events": sound_events(k, K),
        "music": music_plan(k, main, drop, float(b.get("music", {}).get("gain_db", 0.0))) if main else [],
        "mix": b.get("mix", "voice"),
        "allowed_numbers": [str(x) for x in b.get("allowed_numbers", [])],
        "end_card": cta_kind == "follow",
        "cta": {"kind": cta_kind, "line": T["cta_line"]},
        "speaker": {"face": [round(fx, 1), round(fy, 1)], "camera": [cam_w, cam_h], "states": states},
    }
    (WORK / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    (WORK / "captions.json").write_text(json.dumps(caps, ensure_ascii=False, indent=2))
    return plan


if __name__ == "__main__":
    p = build()
    print(json.dumps({"duration": p["duration"], "captions": len(p["captions"]), "events": len(p["sound_events"])}))
