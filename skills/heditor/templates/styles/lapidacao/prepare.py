"""Cut preparation for the style `lapidacao`: choose the speech blocks of the source and cut speech + camera.

The style needs one declared blackout right after the hook: ("PAUSE", 0.5, "p_apagao") (black frames + digital
silence; the room goes dark and the spotlight finds the speaker). When two takes of the same phrase are joined, enter
on the next word in a real valley (a retake that opens with the end of the previous word sounds like a repetition).

1. Locate the lines with `heditor transcribe <source> <start> <dur> qa/asr-window.json`.
2. Fill BLOCKS with (key, start_s, end_s, end_radius, start_radius) in seconds of the SOURCE.
   Start/end inside the silence between words; the kit snaps to the energy valley and whole frames.
   Order of BLOCKS = order in the final cut (a cold open can come first).
3. CROP: ffmpeg crop of the speaker ("crop=w:h:x:y"), or None if the whole frame is the speaker.
4. Run `heditor prepare <work>`, then `heditor words <work>` and review words-reviewed.json.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("HEDITOR_KIT", str(Path.home() / ".heditor/kit")))
from prepare_cut import prepare_cut  # noqa: E402

SOURCE = "/path/to/source.mp4"
WORK = Path(__file__).resolve().parent
CROP = None  # e.g. "crop=320:238:1548:412" for a webcam tile inside a meeting recording
BLOCKS = [
    # ("hook", 1.62, 7.84, 0.12, 0.12),
    # ("PAUSE", 0.5, "p_apagao"),          # the blackout after the hook (required by the style)
    # ("steps", 16.40, 26.55, 0.15, 0.12),
]

if __name__ == "__main__":
    assert BLOCKS, "fill BLOCKS first"
    edl = prepare_cut(SOURCE, WORK, BLOCKS, crop=CROP, fps=30)
    print(json.dumps({k: edl[k] for k in ("voice_duration", "removed_seconds", "noise_floor_dbfs", "silence_threshold_dbfs")}))
    for c in edl["chunks"]:
        print(c["block"], c["source_in"] and round(c["source_in"], 3), c["source_out"] and round(c["source_out"], 3), "->", round(c["out_start"], 2), round(c["out_end"], 2))
