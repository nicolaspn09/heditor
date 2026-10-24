"""Unit test for `heditor splice` on synthetic clips (ffmpeg only): cut point, frame count, untouched body audio."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import splice as sp  # noqa: E402


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def make_opening(work):
    (work / "render").mkdir(parents=True)
    (work / "composition/assets").mkdir(parents=True)
    (work / "plan.json").write_text(json.dumps({"duration": 1.0}))
    # HyperFrames renders round(D*fps)+1 frames: the splice must use only round(D*fps)
    ff("-f", "lavfi", "-i", "color=c=red:s=108x192:r=30", "-frames:v", "31", "-pix_fmt", "yuv420p",
       str(work / "render/render.mp4"))
    ff("-f", "lavfi", "-i", "sine=f=440:sample_rate=48000:d=1", "-af", "volume=0.3", "-ac", "2", "-c:a", "pcm_s16le",
       str(work / "composition/assets/master.wav"))


def make_body(path):
    ff("-f", "lavfi", "-i", "testsrc2=s=108x192:r=30:d=3", "-f", "lavfi", "-i", "sine=f=660:sample_rate=48000:d=3",
       "-vf", "drawbox=c=black:t=fill:enable='between(t,1,1.19)'", "-af", "volume=0.25", "-ac", "2",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(path))


def test_find_cut_and_splice(tmp_path):
    opening, body, out = tmp_path / "open", tmp_path / "body.mp4", tmp_path / "out.mp4"
    make_opening(opening)
    make_body(body)
    rep = sp.find_cut(body, 0.5, 1.5)
    assert rep["first_black_frames"][0]["frame"] == 30
    res = sp.splice(opening, body, out, cut_frame=30)
    assert res["opening_frames"] == 30
    assert res["frames"] == res["expected_frames"] == 30 + (90 - 30)
    assert res["body_audio"]["lag_samples"] == 0 and res["body_audio"]["correlation"] > 0.999
    assert res["opening_audio"]["lag_samples"] == 0
    assert not res["decode_errors"] and res["ok"]
    assert Path(str(out) + ".splice.json").exists()


def test_opening_before_the_whole_body(tmp_path):
    opening, body, out = tmp_path / "open", tmp_path / "body.mp4", tmp_path / "out.mp4"
    make_opening(opening)
    make_body(body)
    res = sp.splice(opening, body, out, cut_frame=0, match=False)
    assert res["frames"] == 30 + 90 and res["ok"]
