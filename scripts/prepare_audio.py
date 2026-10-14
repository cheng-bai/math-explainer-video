#!/usr/bin/env python3
"""Create bounded, same-voice TTS segments or offline silent budgets."""

import argparse
import asyncio
import hashlib
import json
import math
import subprocess
import shutil
from pathlib import Path
from media_utils import read_config


def audio_duration(path):
    value = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ]
        )
    )
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Invalid audio duration")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--silent", action="store_true")
    mode.add_argument(
        "--audio-dir", type=Path, help="Import 00.mp3, 01.mp3... without online TTS"
    )
    parser.add_argument("--duration", type=float, default=8)
    parser.add_argument("--voice", default="zh-CN-YunxiNeural")
    parser.add_argument("--rate", default="+0%")
    args = parser.parse_args()
    root = args.project.expanduser().resolve()
    cfg = read_config(root)
    lines = json.loads((root / "narration.json").read_text(encoding="utf-8"))
    if (
        not isinstance(lines, list)
        or not lines
        or not all(isinstance(t, str) and t.strip() for t in lines)
    ):
        parser.error("narration.json must be a non-empty array of spoken-text strings")
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("duration must be positive and finite")
    (root / "audio").mkdir(exist_ok=True)

    async def generate(index, text):
        import edge_tts

        path = root / "audio" / f"{index:02d}.mp3"
        meta = path.with_suffix(".json")
        fingerprint = hashlib.sha256(
            json.dumps([text, args.voice, args.rate], ensure_ascii=False).encode()
        ).hexdigest()
        if path.exists() and path.stat().st_size > 1000 and meta.exists():
            try:
                if (
                    json.loads(meta.read_text(encoding="utf-8")).get("hash")
                    == fingerprint
                ):
                    audio_duration(path)
                    return path
            except (ValueError, subprocess.CalledProcessError):
                pass
        temporary = path.with_suffix(".tmp.mp3")
        for attempt in range(3):
            try:
                await asyncio.wait_for(
                    edge_tts.Communicate(text, args.voice, rate=args.rate).save(
                        str(temporary)
                    ),
                    timeout=30,
                )
                if temporary.stat().st_size <= 1000:
                    raise ValueError("Empty audio")
                audio_duration(temporary)
                temporary.replace(path)
                meta.write_text(
                    json.dumps(
                        {"hash": fingerprint, "voice": args.voice, "rate": args.rate}
                    ),
                    encoding="utf-8",
                )
                return path
            except Exception as error:
                temporary.unlink(missing_ok=True)
                print(
                    f"Segment {index}: attempt {attempt + 1}: {type(error).__name__}",
                    flush=True,
                )
                if attempt < 2:
                    await asyncio.sleep(attempt + 1)
        raise RuntimeError(
            f"Segment {index}: TTS failed after 3 attempts; no mixed-voice fallback. No timestamps updated."
        )

    async def prepare():
        # Serial requests have proved more reliable than parallel TTS requests.
        if args.silent:
            paths = [None] * len(lines)
        elif args.audio_dir:
            source = args.audio_dir.expanduser().resolve()
            imported = [source / f"{i:02d}.mp3" for i in range(len(lines))]
            for path in imported:
                audio_duration(
                    path
                )  # Validate every source before updating local audio.
            paths = []
            for i, path in enumerate(imported):
                destination = root / "audio" / f"{i:02d}.mp3"
                if path != destination:
                    shutil.copyfile(path, destination)
                destination.with_suffix(".json").write_text(
                    json.dumps(
                        {
                            "source": "local import",
                            "audio_sha256": hashlib.sha256(
                                destination.read_bytes()
                            ).hexdigest(),
                        }
                    ),
                    encoding="utf-8",
                )
                paths.append(destination)
        else:
            paths = [await generate(i, text) for i, text in enumerate(lines)]
        result = []
        for index, (text, path) in enumerate(zip(lines, paths)):
            duration = 0 if args.silent else audio_duration(path)
            budget = (
                math.ceil(
                    (args.duration if args.silent else duration + 0.6) * cfg["fps"]
                )
                / cfg["fps"]
            )
            result.append(
                {
                    "index": index,
                    "text": text,
                    "audio": str(path) if path else None,
                    "audio_duration": duration,
                    "duration_s": budget,
                }
            )
        temporary = root / "timestamps.tmp.json"
        temporary.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(root / "timestamps.json")
        (root / "narration.txt").write_text("\n".join(lines), encoding="utf-8")
        print(f"{len(result)} segments; {sum(d['duration_s'] for d in result):.2f}s")

    asyncio.run(prepare())


if __name__ == "__main__":
    main()
