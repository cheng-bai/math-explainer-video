#!/usr/bin/env python3
"""Read-only dependency checks; never installs or changes configuration."""

import argparse
import importlib.util
import shutil
import subprocess
from media_utils import subtitle_font


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--silent", action="store_true", help="Skip online TTS package requirement"
    )
    args = parser.parse_args()
    failures = []
    for tool in ("manim", "ffmpeg", "ffprobe", "latex", "dvisvgm"):
        path = shutil.which(tool)
        print(f"{tool}: {path or 'MISSING'}")
        if not path:
            failures.append(tool)
    for module in ("PIL",) if args.silent else ("PIL", "edge_tts"):
        available = importlib.util.find_spec(module) is not None
        print(f"{module}: {'OK' if available else 'MISSING in current Python'}")
        if not available:
            failures.append(module)
    if not args.silent and importlib.util.find_spec("edge_tts") is not None:
        import edge_tts

        print("edge-tts version:", edge_tts.__version__)
    if shutil.which("manim"):
        result = subprocess.run(["manim", "--version"], capture_output=True, text=True)
        print((result.stdout + result.stderr).strip())
        if result.returncode:
            failures.append("Manim runtime")
    try:
        print("Subtitle font:", subtitle_font())
    except (ValueError, RuntimeError) as error:
        print(error)
        failures.append("CJK font")
    print(
        "No network requests performed. LaTeX/font rendering is validated by the example, not this inventory."
    )
    if failures:
        raise SystemExit("Missing: " + ", ".join(failures))


if __name__ == "__main__":
    main()
