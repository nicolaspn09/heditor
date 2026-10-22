"""Baseline composition for a heditor cut (runs as-is; then make it YOURS).

This file is the starting point, not the style. Read references/workflow.md and the chosen style
(references/styles/<style>.md) or creative mode (references/creative-mode.md), write DESIGN.md, and then
rewrite scenes(), CSS, JS, sound_events() and music_plan() so the edit is built for THIS speech.

Run:  heditor produce <work> music:<id> <drop_s>    (or a path to your own licensed track)
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("HEDITOR_KIT", str(Path.home() / ".heditor/kit")))
import reelkit as rk  # noqa: E402

WORK = Path(__file__).resolve().parent
CTA = 4.5
HOOK = ""          # on-screen hook for the first seconds; must reflect the spoken hook (empty = first caption)
QUESTION = ""      # comment question for the CTA (empty = brand default)
SEED = 20261013
MIX = "voice"      # "presence" for paid ads and creative mode (sound-design.md: mix profiles)


def load():
    words_file = WORK / "words-reviewed.json" if (WORK / "words-reviewed.json").exists() else WORK / "words.json"
    words = rk.load_words(words_file)
    edl = json.loads((WORK / "edl.json").read_text())
    return words, round(edl["voice_duration"], 3)


def keys(words, voice_end):
    """Key moments. Replace the automatic picks with the words that carry YOUR argument."""
    content = [w for w in words if len(rk.plain(w["word"])) >= 6 and w["start"] > 2.0 and w["start"] < voice_end - 1.0]
    picks, last = [], -9.0
    for w in sorted(content, key=lambda x: -len(rk.plain(x["word"]))):
        if all(abs(w["start"] - p["start"]) > 3.0 for p in picks):
            picks.append(w)
        if len(picks) == 5:
            break
    picks.sort(key=lambda x: x["start"])
    k = {f"emph{i}": p["start"] for i, p in enumerate(picks)}
    k["emphWords"] = [p["shown"].strip(".,?!:;").upper() for p in picks]
    first_end = next((w["end"] for w in words if w["word"].endswith((".", "?", "!"))), min(3.0, voice_end))
    k["hook_end"] = round(min(first_end, 4.0), 3)
    k["voice_end"] = voice_end
    k["duration"] = round(voice_end + CTA, 3)
    return k


def scenes(hook, question, brand):
    return f"""
<div class="hook" id="hook"><div class="h2">{hook}</div></div>
<div id="beat"><span id="beat-w"></span></div>
<div class="cta-q" id="ctaq"><div class="q2">{question}</div><div class="q3">{rk.icon("message-circle")}<span>{brand["comment"]}</span></div></div>
<div id="card"><img src="assets/logo.png" alt="logo"><div class="handle">{brand["handle"]}</div>
  <div id="fbtn"><span id="fb-a">{brand["follow"]}</span><span id="fb-b">{rk.icon("check")}{brand["following"]}</span></div></div>
<div id="ripple"></div><div id="finger">{rk.icon("pointer")}</div>
"""


CSS = r"""
.hook .h2{font-size:104px;padding:0 60px;text-wrap:balance}
#beat{position:absolute;left:0;top:300px;width:1080px;text-align:center;z-index:12;opacity:0}
#beat-w{display:inline-block;font-family:Anton;font-size:120px;color:#000;background:var(--accent);padding:0 .25em;border-radius:.12em;transform:rotate(-3deg)}
#card{position:absolute;left:240px;top:760px;width:600px;z-index:14;opacity:0;text-align:center}
#card img{width:180px;height:180px;object-fit:contain}
.handle{font-family:Geist;font-weight:700;font-size:48px;margin-top:16px;color:var(--accent)}
#fbtn{position:relative;margin:24px auto 0;width:440px;height:104px;border-radius:26px;background:var(--accent);color:#000;font-family:Geist;font-size:50px;font-weight:700}
#fbtn span{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:12px}
#fb-b{opacity:0;color:var(--accent)}#fb-b .ic{width:50px;height:50px;stroke-width:3}
#finger{left:640px;top:1120px}#ripple{left:500px;top:1040px}
"""

JS = r"""
gsap.set('#hook',{opacity:1});
out('#hook',K.hook_end,{y:-40});
K.emphWords.forEach((w,i)=>{const t=K['emph'+i];
  S('#beat-w',{textContent:w},t-.06);
  FT('#beat',{opacity:0,scale:1.8},{opacity:1,scale:1,duration:.16,ease:'power4.in'},t-.06);
  punch(t,1.1,.35);shake(t+.1,8);
  TO('#beat',{opacity:0,duration:.2},t+.9);});
const C=K.voice_end;
TO('#rig',{scale:.2,x:430,y:300,opacity:0,duration:.32,ease:'expo.in'},C-.2);TO('#rig-aura',{opacity:0,duration:.2},C-.2);
flash(C,.3,.25);
FT('#ctaq .q2',{opacity:0,y:40},{opacity:1,y:0,duration:.3,ease:'back.out(2)'},C+.1);
FT('#ctaq .q3',{opacity:0,y:30},{opacity:1,y:0,duration:.25},C+.45);
FT('#card',{opacity:0,y:200},{opacity:1,y:0,duration:.45,ease:'expo.out'},C+.8);
FT('#finger',{opacity:0,x:120,y:160},{opacity:1,x:0,y:0,duration:.4,ease:'power3.out'},C+1.5);
TO('#finger',{x:-150,y:-100,duration:.3,ease:'power2.inOut'},C+1.9);
TO('#finger',{scale:.85,duration:.06},C+2.2);TO('#finger',{scale:1,duration:.12},C+2.28);
FT('#ripple',{opacity:.9,scale:.3},{opacity:0,scale:3,duration:.45},C+2.22);
TO('#fbtn',{backgroundColor:'rgba(0,0,0,0)',boxShadow:'inset 0 0 0 4px var(--accent)',duration:.2},C+2.28);
S('#fb-a',{opacity:0},C+2.28);S('#fb-b',{opacity:1},C+2.28);
TO('#finger',{opacity:0,duration:.2},C+2.7);
TO(['#ctaq','#card'],{opacity:0,duration:.25},D-.25);
"""


def sound_events(k):
    ev = [{"time": 0.0, "category": "bass_impact", "variant": 0, "gain_db": -12, "context": "opening"},
          {"time": max(0.0, k["hook_end"] - 0.1), "category": "whoosh", "variant": 0, "gain_db": -15, "context": "hook out"}]
    for i in range(len(k["emphWords"])):
        ev.append({"time": round(k[f"emph{i}"] - 0.08, 3), "category": "stamp", "variant": 0, "gain_db": -14, "context": f"beat {i}"})
    c = k["voice_end"]
    ev += [{"time": c - 0.15, "category": "whoosh", "variant": 1, "gain_db": -12, "context": "to CTA"},
           {"time": c + 2.2, "category": "click", "variant": 0, "gain_db": -9, "context": "follow tap"},
           {"time": c + 2.3, "category": "level_up", "variant": 0, "gain_db": -13, "context": "following"}]
    return sorted(ev, key=lambda x: x["time"])


def music_plan(k, track, drop_s):
    mid = k.get("emph1", k["voice_end"] / 2)
    return [
        {"start": 0.0, "end": mid - 0.35, "mode": "lowpass", "gain_db": -6, "track": track, "src": max(0.0, drop_s - mid)},
        {"start": mid - 0.35, "end": mid - 0.03, "mode": "silence"},
        {"start": mid - 0.03, "end": k["duration"], "mode": "full", "gain_db": 0, "track": track, "src": drop_s,
         "fade_out": 1.0},
    ]


def build(track, drop_s):
    brand = rk.load_brand(WORK)
    rk.setup_assets(WORK)
    rk.ensure_icons(["message-circle", "check", "pointer"])
    a = WORK / "composition/assets"
    # Revisions may already contain derived media from a different cut.
    rk.prepare_camera(WORK)
    rk.prepare_voice(WORK)
    words, voice_end = load()
    k = keys(words, voice_end)
    caps = rk.captions(words, voice_end)
    hook = HOOK or caps[0]["text"].upper()
    question = QUESTION or ("E você, o que acha?" if brand.get("lang", "pt") == "pt" else "What do you think?")
    card_w, card_h = 960, 714
    k["rigStates"] = rk.rig_states(card_w, card_h)
    k["rig"] = [[0.0, "hero"]]
    k["segments"] = rk.jump_segments(WORK, rk.track_faces(WORK), voice_end)
    k["seed"] = SEED
    videos = [{"id": "cam-hd", "start": 0, "duration": voice_end, "track": 0, "src": "camera-hd.mp4"}]
    markup = rk.page(title=f"{brand['name']} cut", duration=k["duration"], card_w=card_w, card_h=card_h,
                     face_origin="50% 45%", videos=videos, scenes_html=scenes(hook, question, brand), css=CSS, js=JS,
                     keys=k, caps=caps, caption_mode="pill", brand_work=WORK)
    (WORK / "composition/index.html").write_text(markup)
    plan = {"duration": k["duration"], "voice_end": voice_end, "keys": k, "captions": caps,
            "sound_events": sound_events(k), "music": music_plan(k, track, drop_s),
            "music_ref": [k.get("emph1", 0.0), k["voice_end"]], "cta_boost_db": 5,
            "mix": MIX}
    (WORK / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    (WORK / "captions.json").write_text(json.dumps(caps, ensure_ascii=False, indent=2))
    return plan
