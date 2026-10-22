"""Cut preparation for the style `reacao`: choose the speech blocks of the raw take and cut speech + camera.

The raw take is the speaker talking about a post/news. When the subject is inside the same recording (a split-screen
export, a screen share with the webcam beside it), crop only the speaker here and cut the subject later with
`heditor region <work> <name> <crop>` or a "region" source in beats.json: it reuses this EDL frame for frame.

1. Locate the lines with `heditor transcribe <source> <start> <dur> qa/asr-window.json`.
2. Fill BLOCKS with (key, start_s, end_s, end_radius, start_radius) in seconds of the SOURCE.
   Start/end inside the silence between words; the kit snaps to the energy valley and whole frames.
3. CROP: ffmpeg crop of the speaker ("crop=w:h:x:y"), or None if the whole frame is the speaker. Leave burned
   captions of an earlier edit out of the crop. The matte needs the speaker large: ~900 px wide or more.
4. Run `heditor prepare <work>`, then `heditor words <work>` and review words-reviewed.json (names of products,
   companies and sites exactly as they are written).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("HEDITOR_KIT", str(Path.home() / ".heditor/kit")))
from prepare_cut import prepare_cut  # noqa: E402

SOURCE = "/path/to/source.mp4"
WORK = Path(__file__).resolve().parent
CROP = None  # e.g. "crop=1440:1112:0:1448" for the camera half of a split-screen export
FPS = 30     # the source frame rate (phones: 30; the backdrop region is cut at the same rate)
BLOCKS = [
    # ("hook", 0.06, 5.70, 0.10, 0.05),
    # ("body", 5.70, 66.20, 0.10, 0.10),
]

if __name__ == "__main__":
    assert BLOCKS, "fill BLOCKS first"
    edl = prepare_cut(SOURCE, WORK, BLOCKS, crop=CROP, fps=FPS)
    print(json.dumps({k: edl[k] for k in ("voice_duration", "removed_seconds", "noise_floor_dbfs", "silence_threshold_dbfs")}))
    for c in edl["chunks"]:
        print(c["block"], c["source_in"] and round(c["source_in"], 3), c["source_out"] and round(c["source_out"], 3), "->", round(c["out_start"], 2), round(c["out_end"], 2))
