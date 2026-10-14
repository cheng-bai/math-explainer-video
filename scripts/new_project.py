#!/usr/bin/env python3
import argparse, json, re, shutil
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("slug")
ap.add_argument("--root", type=Path, default=Path.cwd() / "work")
ap.add_argument("--aspect", choices=["9:16", "16:9", "1:1"], default="16:9")
ap.add_argument("--width", type=int, default=None)
ap.add_argument("--fps", type=int, default=24)
a = ap.parse_args()
if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", a.slug):
    ap.error("slug must be lowercase words separated by hyphens")
if a.fps <= 0:
    ap.error("fps must be positive")
w = a.width or (1080 if a.aspect != "16:9" else 1920)
x, y = map(int, a.aspect.split(":"))
h = round(w * y / x)
if w < 64 or h < 64 or w % 2 or h % 2:
    ap.error("width and derived height must be positive even dimensions >= 64")
a.root.expanduser().mkdir(parents=True, exist_ok=True)
r = a.root.expanduser() / a.slug
i = 2
while r.exists():
    r = a.root.expanduser() / f"{a.slug}-{i}"
    i += 1
r.mkdir()
(r / "project.json").write_text(
    json.dumps(
        {"width": w, "height": h, "frame_width": x, "frame_height": y, "fps": a.fps},
        indent=2,
    )
)
(r / "narration.json").write_text("[]\n")
shutil.copyfile(
    Path(__file__).resolve().parents[1] / "assets/scene-template.py", r / "script.py"
)
print(r.resolve())
