"""Portable configuration, fonts and concat paths; no network or import side effects."""

import json
import math
import os
from pathlib import Path


def read_config(project):
    cfg = json.loads((project / "project.json").read_text(encoding="utf-8"))
    for key in ("width", "height", "fps", "frame_width", "frame_height"):
        value = cfg.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"project.json: {key} must be finite and positive")
    for key in ("width", "height"):
        if not isinstance(cfg[key], int) or cfg[key] < 64 or cfg[key] % 2:
            raise ValueError(f"project.json: {key} must be an even integer >= 64")
    return cfg


def concat_line(path):
    # FFconcat quoting: close quotes, escape a quote outside, then reopen.
    value = str(path).replace("\\", "/")
    if any(c in value for c in "\n\r\x00"):
        raise ValueError("Concat paths cannot contain newline or NUL")
    return "file '" + value.replace("'", "'\\''") + "'"


def subtitle_font():
    override = os.environ.get("MATH_VIDEO_FONT_FILE")
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise ValueError("MATH_VIDEO_FONT_FILE does not name a file")
        return str(path)
    candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for path in candidates:
        if Path(path).is_file():
            return path
    raise RuntimeError(
        "No CJK subtitle font; set MATH_VIDEO_FONT_FILE to a Chinese font file"
    )
