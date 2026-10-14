#!/usr/bin/env python3
"""Render an author-provided OverviewScene and export PNG + image-based PDF."""

import argparse
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--scene", default="OverviewScene")
    parser.add_argument("--manim", default=shutil.which("manim"))
    args = parser.parse_args()
    if not args.manim:
        parser.error("Manim is missing")
    root = args.project.expanduser().resolve()
    media = root / "overview_media"
    subprocess.run(
        [
            args.manim,
            "-s",
            "--media_dir",
            str(media),
            "--progress_bar",
            "none",
            "--verbosity",
            "WARNING",
            "script.py",
            args.scene,
        ],
        cwd=root,
        check=True,
    )
    images = list((media / "images" / "script").glob(args.scene + "_*.png"))
    if not images:
        raise RuntimeError("Manim produced no overview PNG")
    output = root / "overview.png"
    shutil.copyfile(max(images, key=lambda path: path.stat().st_mtime), output)
    from PIL import Image, JpegImagePlugin  # Register PDF's JPEG encoder explicitly.

    image = Image.open(output).convert("RGB")
    image.save(root / "overview.pdf", resolution=150)
    print(f"OVERVIEW_READY {output.name} {image.size}; overview.pdf is image-based")


if __name__ == "__main__":
    main()
