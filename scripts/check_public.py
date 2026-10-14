#!/usr/bin/env python3
"""Check the actual publication file set for obvious local data and credentials."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", "__pycache__", "work", ".ruff_cache"}
PRIVATE_PATH = re.compile(r"/(?:Users|home)/[^/\s]+/")
TOKEN = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


def main():
    if (ROOT / ".git").exists():
        names = (
            subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
            .decode()
            .split("\0")
        )
        files = [ROOT / name for name in names if name]
        if not files:
            raise SystemExit(
                "No staged/tracked files; stage the explicit publication set first"
            )
    else:
        files = [
            path
            for path in ROOT.rglob("*")
            if path.is_file() and not set(path.relative_to(ROOT).parts) & SKIP
        ]
    errors = []
    for path in files:
        name = path.relative_to(ROOT)
        if path.name.startswith(".env") or path.suffix.lower() in {
            ".mp3",
            ".mp4",
            ".wav",
            ".ttf",
            ".otf",
            ".ttc",
        }:
            errors.append(f"Unexpected private/generated/binary file: {name}")
        if path.stat().st_size > 5_000_000:
            errors.append(f"Large file: {name}")
        if path.suffix in {".png", ".jpg"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"Unexpected non-text file: {name}")
            continue
        if PRIVATE_PATH.search(text) or TOKEN.search(text):
            errors.append(f"Possible private path/credential: {name}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"PUBLIC_CHECK_OK {len(files)} files; pattern scan is not a rights or security guarantee"
    )


if __name__ == "__main__":
    main()
