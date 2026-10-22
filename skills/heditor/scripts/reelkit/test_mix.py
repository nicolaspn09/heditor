"""Unit tests for mix profiles and the music presence floor (no audio files needed)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import reelkit as rk  # noqa: E402


def test_default_profile_is_voice_first():
    tg = rk.mix_targets({})
    assert tg["profile"] == "voice" and tg["music_median_db"] == -21.5 and tg["bed_p95_db"] == -12.0
    assert not tg["asr_check_required"]


def test_presence_profile_by_name_and_dict():
    for plan in ({"mix": "presence"}, {"mix": {"profile": "presence"}}, {"mix_profile": "presence"}):
        tg = rk.mix_targets(plan)
        assert tg["profile"] == "presence" and tg["music_median_db"] == -15.0 and tg["asr_check_required"]
        assert tg["filtered_makeup_db"] > 0 and tg["presence_gap_s"] <= 2.0


def test_legacy_override_dict_keeps_working():
    tg = rk.mix_targets({"mix": {"music_median_db": -15.0, "bed_p95_db": -7.0, "within_10db_pct": 30}})
    assert tg["music_median_db"] == -15.0 and tg["within_10db_pct"] == 30 and tg["profile"] == "voice+custom"


def test_unknown_profile_raises():
    with pytest.raises(ValueError):
        rk.mix_targets({"mix": "loud"})


def test_music_gaps_finds_quiet_runs_only_in_eligible_windows():
    hop = 0.4
    levels = np.full(50, -40.0)          # bed at -40 dBFS
    levels[10:25] = -70.0                # 6 s where the bed vanishes (e.g. a long muffled section)
    levels[30:33] = -70.0                # 1.2 s dip
    elig = np.ones(50, bool)
    elig[30:33] = False                  # ...declared silence: ignored
    gaps, present = rk.music_gaps(levels, -18.0, elig, hop, -30.0)
    assert gaps == [(4.0, 10.0)]
    assert present == pytest.approx(100 * (47 - 15) / 47, abs=0.2)


def test_music_gaps_bridges_a_bed_that_only_peeks_out():
    levels = np.full(40, -70.0)
    levels[[8, 9, 18]] = -40.0           # two short peeks inside a 12 s stretch where the bed is gone
    gaps, _ = rk.music_gaps(levels[:30], -18.0, np.ones(30, bool), 0.4, -30.0)
    assert gaps == [(0.0, 12.0)]


def test_music_gaps_ignores_short_blips_and_empty_plans():
    gaps, present = rk.music_gaps(np.array([-40.0, -70.0, -40.0, -40.0, -40.0]), -18.0, np.ones(5, bool), 0.4, -30.0)
    assert gaps == [] and present < 100
    gaps, present = rk.music_gaps(np.full(5, -70.0), -18.0, np.zeros(5, bool), 0.4, -30.0)
    assert gaps == [] and present == 100.0
