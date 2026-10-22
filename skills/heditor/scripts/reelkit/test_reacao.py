"""Unit tests for the style `reacao` helpers (no browser, no models): geometry and the EDL-synced region clip."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import reacaokit as rx  # noqa: E402


def test_view_centres_focus_and_scales_to_width():
    x, y, s = rx.view(2000, 6000, [1000, 3000, 1000], anchor_y=760)
    assert s == 1.08
    assert abs((x + s * 1000) - 540) < 0.01 and abs((y + s * 3000) - 760) < 0.01


def test_view_clamps_inside_a_large_image():
    x, y, s = rx.view(1080, 4000, [100, 50, 1080], anchor_y=760)   # top-left corner of a tall page
    assert x == 0 and y == 0 and s == 1.0
    x, y, s = rx.view(1080, 4000, [540, 3990, 1080], anchor_y=760)  # bottom of the page
    assert y == round(1920 - 4000, 2)


def test_view_never_leaves_a_band_with_a_landscape_recording():
    for focus, anchor in (([681, 597, 2000], 760), ([681, 1100, 1362], 400), ([60, 60, 700], 900)):
        x, y, s = rx.view(1362, 1194, focus, anchor_y=anchor)
        assert x <= 0 and x + s * 1362 >= 1080 - 0.01      # covers the width
        assert y <= 0 and y + s * 1194 >= 1300 - 0.01      # covers the top and reaches the speaker's head
    x, y, s = rx.view(1362, 1194, [681, 1100, 1362], anchor_y=400, min_bottom=1100)
    assert abs(s - 1100 / 1194) < 1e-4 and y + s * 1194 >= 1100 - 0.01   # a lower floor shows more page width


def test_speaker_states_place_the_face_and_keep_the_body_low():
    st = rx.speaker_states(face_x=720, face_y=640, cam_w=1440, cam_h=1112)
    for name, (size, fx, fy) in rx.SPEAKER_STATES.items():
        v = st[name]
        assert abs(v["x"] + v["s"] * 720 - fx) < 0.2, name
        assert v["bottom"] >= 1600 - 0.2, name
        if v["bottom"] > 1600.5:
            assert abs(v["face_y"] - fy) < 0.2, name
    assert st["punch"]["s"] > st["hero"]["s"] > st["center"]["s"] > st["small"]["s"]


def test_region_clip_follows_the_edl(tmp_path):
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x480:r=30:d=4",
                    "-pix_fmt", "yuv420p", str(src)], check=True)
    work = tmp_path / "work"
    (work / "composition/assets").mkdir(parents=True)
    edl = {"source": str(src), "fps": 30, "chunks": [
        {"block": "a", "source_in": 0.5, "source_out": 1.5, "out_start": 0.0, "out_end": 1.0},
        {"block": "p", "pause": True, "source_in": None, "source_out": None, "out_start": 1.0, "out_end": 1.2},
        {"block": "b", "source_in": 2.0, "source_out": 3.0, "out_start": 1.2, "out_end": 2.2}]}
    (work / "edl.json").write_text(json.dumps(edl))
    name = rx.region_clip(work, "top", "crop=320:200:0:0")
    out = work / "composition/assets" / name
    n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries",
                        "stream=nb_read_frames,width,height", "-of", "csv=p=0", str(out)],
                       capture_output=True, text=True, check=True).stdout.strip().split(",")
    assert n[:2] == ["320", "200"]
    assert int(n[2]) == 30 + 6 + 30
    assert rx.region_clip(work, "top", "crop=320:200:0:0") == name   # cached
