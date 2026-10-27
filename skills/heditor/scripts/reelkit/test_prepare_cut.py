"""Tests for prepare_cut: pause trims that land on a scene seam (AI avatar studio videos, spliced takes)."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import prepare_cut as pc  # noqa: E402

FPS = 25


def test_cut_on_seam_moves_the_window_onto_the_seam():
    # pause 1.0-2.0 s at 25 fps, edge 0.12: default removal [28, 47)
    r0, r1 = 28, 47
    # seam in the trailing kept edge (first frame of the new scene = 48): window shifted right, same width
    assert pc.cut_on_seam(r0, r1, 1.0, 2.0, 0.0, FPS, [1.92]) == (29, 48, 1.92)
    # seam in the leading kept edge (frame 26): window starts on the seam, same width
    assert pc.cut_on_seam(r0, r1, 1.0, 2.0, 0.0, FPS, [1.04]) == (26, 45, 1.04)
    # seam already inside the removed window: one jump already, unchanged
    assert pc.cut_on_seam(r0, r1, 1.0, 2.0, 0.0, FPS, [1.5]) == (28, 47, 1.5)
    # seam outside the pause or no seams: unchanged
    assert pc.cut_on_seam(r0, r1, 1.0, 2.0, 0.0, FPS, [2.6]) == (28, 47, None)
    assert pc.cut_on_seam(r0, r1, 1.0, 2.0, 0.0, FPS, None) == (28, 47, None)
    # block that starts later in the source: seams are source times
    assert pc.cut_on_seam(r0, r1, 1.0, 2.0, 10.0, FPS, [11.92]) == (29, 48, 11.92)


def _source(path, seam):
    """Red scene, then blue from `seam` s; tone 0.3-1.0 s and 2.0-2.7 s, silence elsewhere."""
    subprocess.run(["ffmpeg", "-v", "error", "-y",
                    "-f", "lavfi", "-i", f"color=c=red:s=64x112:r={FPS}:d=3",
                    "-f", "lavfi", "-i", "sine=f=440:sample_rate=48000:d=3",
                    "-vf", f"drawbox=c=blue:t=fill:enable='gte(t,{seam})'",
                    "-af", "volume=0.4,volume=enable='not(between(t,0.3,1.0)+between(t,2.0,2.7))':volume=0",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(path)], check=True)


def _blue_frames(video):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", "scale=8:14", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 14, 8, 3).astype(float)
    return (f[..., 2].mean(axis=(1, 2)) > f[..., 0].mean(axis=(1, 2))).tolist()


def test_prepare_cut_joins_the_scenes_at_the_seam(tmp_path):
    src = tmp_path / "avatar.mp4"
    _source(src, 1.92)
    blocks = [("fala", 0.04, 2.96, 0.04, 0.04)]
    plain = pc.prepare_cut(src, tmp_path / "plain", blocks, crop=None, fps=FPS)
    seamed = pc.prepare_cut(src, tmp_path / "seamed", blocks, crop=None, fps=FPS, seams=[1.92])
    # same timeline: the trim removes the same time, only its position moves
    assert abs(plain["voice_duration"] - seamed["voice_duration"]) < 1e-6
    assert [t["removed_s"] for t in plain["silence_trims"]] == [t["removed_s"] for t in seamed["silence_trims"]]
    joint = seamed["chunks"][1]
    assert abs(joint["source_in"] - 1.92) < 1e-6
    assert seamed["silence_trims"][0]["seam"] == 1.92
    # without seams the cut lands 1 frame before the pose reset (two jumps); with seams the colour changes on the cut
    assert plain["chunks"][1]["source_in"] < 1.92
    blue = _blue_frames(tmp_path / "seamed/composition/assets/camera-src.mp4")
    first_blue = blue.index(True)
    assert first_blue == round(joint["out_start"] * FPS)
    assert all(blue[first_blue:]) and not any(blue[:first_blue])
    json.dumps(seamed)  # the edl stays serialisable


def test_alpha_floor_clears_background_haze_and_keeps_the_edge():
    import depthkit as dk
    m = np.array([0.0, 0.05, 0.09, 0.5, 1.0])
    out = dk.alpha_floor(m, 0.09)
    assert out[0] == 0 and out[1] == 0 and out[2] == 0      # haze gone
    assert 0.4 < out[3] < 0.5 and out[4] == 1.0               # soft edge kept, person opaque
    assert np.array_equal(dk.alpha_floor(m, 0), m)            # floor=0 keeps the old behaviour
