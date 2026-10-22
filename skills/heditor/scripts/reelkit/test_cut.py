"""Integrity tests for any heditor cut. Usage: CUT_WORK=<work_dir> pytest -q test_cut.py

Reels (plan without "mode") keep the historical rules. Long-form plans ("mode": "long", `heditor long produce`)
use the same tests with long-form limits: no 180 s cap, the CTA follows plan["cta"]["kind"] (follow or youtube),
captions may be off (burn: false), the voice starts at plan["voice_offset"] and pauses up to 0.6 s are accepted.
"""

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

WORK = Path(os.environ["CUT_WORK"])
sys.path.insert(0, str(Path(__file__).parent))
import reelkit as rk  # noqa: E402
BRAND = rk.load_brand(WORK)
PLAN = json.loads((WORK / "plan.json").read_text())
HTML = (WORK / "composition/index.html").read_text()
_words = WORK / "words-reviewed.json" if (WORK / "words-reviewed.json").exists() else WORK / "words.json"
SOURCE = json.loads(_words.read_text())
SOURCE = SOURCE if isinstance(SOURCE, list) else SOURCE["words"]
LONG = PLAN.get("mode") == "long"
OFF = float(PLAN.get("voice_offset", 0.0))


def test_caption_tokens_match_source_once():
    if LONG and not PLAN["captions"]:
        return  # burned captions turned off (subtitles exported as SRT/VTT)
    out = Counter((w["word"].strip(), round(w["start"], 3)) for c in PLAN["captions"] for w in c["words"])
    src = Counter((w["word"].strip(), round(float(w["start"]), 3)) for w in SOURCE)
    assert out == src


def test_captions_ordered_without_overlap():
    caps = PLAN["captions"]
    if not caps:
        assert LONG, "a Reel must have captions"
        return
    for a, b in zip(caps, caps[1:]):
        assert a["start"] < a["end"] <= b["start"] + 1e-6
    assert caps[-1]["end"] <= PLAN["voice_end"] + 1e-6


# Short Reels stay within 70 s by default. A long-form cut (e.g. a narrated documentary of ~90 s) declares
# "max_duration" in plan.json (or HEDITOR_MAX_DURATION); Instagram Reels accept up to 180 s.
MAX_DURATION = float(PLAN.get("max_duration") or os.environ.get("HEDITOR_MAX_DURATION") or 70)


def test_duration_and_cta():
    if LONG:
        cta = PLAN.get("cta", {})
        assert abs(PLAN["duration"] - (PLAN["voice_end"] + cta.get("duration", 0))) < 0.01
        assert PLAN["duration"] - PLAN["voice_end"] >= 4.0
        assert BRAND["handle"] in HTML, "CTA must show the brand handle"
        if cta.get("kind") == "youtube":
            assert BRAND["subscribe"] in HTML and BRAND["subscribed"] in HTML, "YouTube CTA: Subscribe -> Subscribed"
        else:
            assert BRAND["follow"] in HTML and BRAND["following"] in HTML, "CTA must show the Follow -> Following state"
        return
    assert MAX_DURATION <= 180, "Instagram Reels are limited to 180 s"
    assert PLAN["duration"] <= MAX_DURATION, f"{PLAN['duration']:.2f} s > max_duration {MAX_DURATION:.0f} s"
    if PLAN.get("end_card") is False:
        # Styles without an end card (e.g. `nativo`): the video ends with the speech, no CTA screen.
        assert 0 <= PLAN["duration"] - PLAN["voice_end"] <= 1.0
        return
    assert PLAN["duration"] - PLAN["voice_end"] >= 4.0
    assert BRAND["handle"] in HTML, "CTA must show the brand handle"
    assert BRAND["follow"] in HTML and BRAND["following"] in HTML, "CTA must show the Follow -> Following state"


def test_sound_events_inside_timeline():
    for ev in PLAN["sound_events"]:
        assert 0 <= ev["time"] < PLAN["duration"]


def test_key_moments_in_speech_order():
    k = PLAN["keys"]
    skip = ("voice_end", "duration", "max_duration", "seed", "brk", "voice_offset", "voice_duration")
    times = [v for key, v in k.items() if isinstance(v, (int, float)) and key not in skip]
    assert all(0 <= t <= PLAN["voice_end"] for t in times)


def test_no_editorial_tags():
    lower = HTML.lower()
    for tag in ["ilustrativ", "imagem de banco", "illustrative", "stock footage", "placeholder", "lorem ipsum"]:
        assert tag not in lower


def test_voice_first_balance():
    b = json.loads((WORK / "qa/balance.json").read_text())
    tg = rk.mix_targets(PLAN)           # profile "voice" (default) or "presence" (+ overrides), see rk.mix
    assert b["music_minus_voice_median_db"] <= float(tg["music_median_db"]) + 0.5
    assert b["bed_minus_voice_p95_db"] <= float(tg["bed_p95_db"]) + 0.5
    assert b["windows_bed_within_10db_pct"] < float(tg["within_10db_pct"])


def test_music_presence():
    """The bed may not vanish inside the speech (quiet intros, long muffled sections): no gap longer than the
    profile's presence_gap_s outside sections declared as "silence". Plans without music are skipped."""
    b = json.loads((WORK / "qa/balance.json").read_text())
    if "music_gaps" not in b:
        return  # mixed before heditor 2.6.0: run `heditor produce` again
    tg = rk.mix_targets(PLAN)
    long = [g for g in b["music_gaps"] if g[1] - g[0] > float(tg["presence_gap_s"]) + 1e-6]
    assert not long, f"music inaudible (> {tg['presence_gap_s']} s under {tg['presence_floor_db']} dB vs voice): {long}"


def test_numbers_only_from_speech():
    visible = re.sub(r"<head>.*?</head>|<script.*?</script>|<style.*?</style>", "", HTML, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", visible)
    spoken = set(re.findall(r"\d+(?:\.\d+)?", " ".join(w["word"] for w in SOURCE)))
    # Numbers on screen must come from the speech; add style-neutral ones in plan["allowed_numbers"].
    allowed = spoken | {str(x) for x in PLAN.get("allowed_numbers", [])}
    numbers = set(re.findall(r"\d+(?:\.\d+)?", text))
    assert numbers <= allowed, numbers - allowed


def test_no_dead_air():
    """Uncut pauses read as sloppy editing: no silence inside the speech may exceed 0.45 s (heditor gaps)."""
    from gaps import find_gaps
    # declared dramatic pauses (edl.json "pauses", style trailer) count only for the silence around them
    long = [g for g in find_gaps(WORK) if g.get("excess", g["dur"]) > PLAN.get("max_gap_s", 0.6 if LONG else 0.45)]
    assert not long, [(round(g["start"], 2), g["dur"], g["before"], g["after"]) for g in long]


def test_normalized_voice_matches_cut_duration():
    """A revision must not reuse the old voice-master while captions and camera use a shorter cut."""
    import wave

    assets = WORK / "composition/assets"
    durations = {}
    for name in ("voice-raw.wav", "voice-master.wav"):
        with wave.open(str(assets / name)) as audio:
            durations[name] = audio.getnframes() / audio.getframerate()
    assert abs(durations["voice-raw.wav"] - (PLAN["voice_end"] - OFF)) < 0.01
    assert abs(durations["voice-master.wav"] - durations["voice-raw.wav"]) < 0.01, durations
