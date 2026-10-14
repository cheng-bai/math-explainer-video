import argparse, json, subprocess, re, math, shutil, hashlib
from media_utils import read_config, concat_line, subtitle_font
from fractions import Fraction
from pathlib import Path

ROOT = None
MEDIA = None


def run(args):
    subprocess.run(args, cwd=ROOT, check=True)


def probe(p):
    return json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(p),
            ]
        )
    )


def stamp(t):
    ms = round(t * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ass_stamp(t):
    cs = round(t * 100)
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def split(text):
    phrases = [p for p in re.split(r"(?<=[，。！？；：])", text) if p]
    parts = []
    buf = ""
    for p in phrases:
        if len(buf) + len(p) > 21 and buf:
            parts.append(buf)
            buf = ""
        while len(p) > 21:
            parts.append(p[:21])
            p = p[21:]
        buf += p
    if buf:
        parts.append(buf)
    return parts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--assemble-only", action="store_true")
    ap.add_argument("--scenes", nargs="+")
    ap.add_argument("--manim", default=shutil.which("manim"))
    a = ap.parse_args()
    ROOT = a.project.expanduser().resolve()
    cfg = read_config(ROOT)
    MEDIA = ROOT / f"media/videos/script/{cfg['height']}p{cfg['fps']:g}"
    data = json.loads((ROOT / "timestamps.json").read_text(encoding="utf-8"))
    scenes = [f"Scene{i + 1:02d}" for i in range(len(data))]
    if not data:
        raise ValueError("No segments; run prepare_audio.py first")
    narration = json.loads((ROOT / "narration.json").read_text(encoding="utf-8"))
    if [d["text"] for d in data] != narration:
        raise ValueError("Narration changed; run prepare_audio.py again")
    for d in data:
        if not math.isfinite(d["duration_s"]) or d["duration_s"] <= 0:
            raise ValueError("Invalid scene duration")
        if (
            not math.isfinite(d["audio_duration"])
            or d["audio_duration"] < 0
            or d["audio_duration"] > d["duration_s"]
        ):
            raise ValueError("Invalid audio duration")
        if d["audio"] and not Path(d["audio"]).is_file():
            raise ValueError("Audio path missing; run prepare_audio.py again")
    (ROOT / "verification.json").unlink(missing_ok=True)
    if a.scenes and any(s not in scenes for s in a.scenes):
        ap.error("Requested scenes must match Scene01..SceneNN")
    manifests = ROOT / "scene_manifest.json"
    records = json.loads(manifests.read_text()) if manifests.exists() else {}

    def signature(entry):
        audio_hash = (
            hashlib.sha256(Path(entry["audio"]).read_bytes()).hexdigest()
            if entry["audio"]
            else None
        )
        return hashlib.sha256(
            json.dumps([cfg, entry, audio_hash], sort_keys=True).encode()
        ).hexdigest()

    source_hash = hashlib.sha256((ROOT / "script.py").read_bytes()).hexdigest()
    if not a.assemble_only:
        if not a.manim:
            ap.error("Manim not found; supply --manim PATH")
        run(
            [
                a.manim,
                "--media_dir",
                str(ROOT / "media"),
                "--progress_bar",
                "none",
                "--verbosity",
                "WARNING",
                "script.py",
                *(a.scenes or scenes),
            ]
        )
        for scene in a.scenes or scenes:
            records[scene] = {
                "input_hash": signature(data[scenes.index(scene)]),
                "source_sha256": source_hash,
            }
        manifests.write_text(json.dumps(records, indent=2), encoding="utf-8")
    for scene, entry in zip(scenes, data):
        if records.get(scene, {}).get("input_hash") != signature(entry):
            raise ValueError(
                f"{scene}: audio/config/timing changed or no render manifest; render this scene again"
            )
    files = [MEDIA / f"{s}.mp4" for s in scenes]
    voiced = all(bool(d["audio"]) for d in data)
    if any(bool(d["audio"]) for d in data) and not voiced:
        ap.error("Use a consistent audio mode for all scenes")
    for entry, p in zip(data, files):
        info = probe(p)
        v = next(x for x in info["streams"] if x["codec_type"] == "video")
        if (v["width"], v["height"]) != (cfg["width"], cfg["height"]):
            raise ValueError(f"{p.name}: inconsistent dimensions")
        if Fraction(v["r_frame_rate"]) != cfg["fps"]:
            raise ValueError(f"{p.name}: inconsistent frame rate")
        if bool(any(x["codec_type"] == "audio" for x in info["streams"])) != voiced:
            raise ValueError(f"{p.name}: audio mode mismatch")
    (ROOT / "concat.txt").write_text(
        "\n".join(concat_line(p.relative_to(ROOT)) for p in files) + "\n",
        encoding="utf-8",
    )
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            "concat.txt",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            "video_clean.mp4",
        ]
    )
    offset = 0
    cues = []
    chapters = []
    for i, (entry, p) in enumerate(zip(data, files)):
        duration = float(probe(p)["format"]["duration"])
        chapters.append({"scene": scenes[i], "start": offset, "duration": duration})
        parts = split(entry["text"]) if voiced else []
        total = sum(len(x) for x in parts)
        cursor = offset
        for part in parts:
            d = entry["audio_duration"] * len(part) / total
            cues.append((cursor, cursor + d, part))
            cursor += d
        if abs(duration - entry["duration_s"]) > max(0.1, 3 / cfg["fps"]):
            raise ValueError(f"{p.name}: animation budget differs from actual duration")
        offset += duration
    (ROOT / "video.srt").write_text(
        "\n\n".join(
            f"{j + 1}\n{stamp(x)} --> {stamp(y)}\n{text}"
            for j, (x, y, text) in enumerate(cues)
        )
        + "\n",
        encoding="utf-8",
    )
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,PingFang SC,42,&H00FFFFFF,&H000000FF,&H00101B2B,&H90101B2B,0,0,0,0,100,100,0,0,1,2,0,2,75,75,175,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    header = header.replace("PlayResX: 1080", f"PlayResX: {cfg['width']}").replace(
        "PlayResY: 1920", f"PlayResY: {cfg['height']}"
    )
    header = header.replace(
        "PingFang SC,42,", f"PingFang SC,{max(16, round(cfg['width'] * 0.031))},"
    ).replace(
        "2,75,75,175,1",
        f"2,{round(cfg['width'] * 0.07)},{round(cfg['width'] * 0.07)},{round(cfg['height'] * 0.04)},1",
    )
    (ROOT / "video.ass").write_text(
        header
        + "\n".join(
            f"Dialogue: 0,{ass_stamp(x)},{ass_stamp(y)},Default,,0,0,0,,{text}"
            for x, y, text in cues
        )
        + "\n",
        encoding="utf-8",
    )
    # Existing FFmpeg lacks libass. Render transparent subtitle cards with
    # Pillow and composite via overlay; keep SRT/ASS as editable deliverables.
    if voiced:
        from PIL import Image, ImageDraw, ImageFont

        cards = ROOT / "subtitle_cards"
        cards.mkdir(exist_ok=True)
        width, height = cfg["width"], cfg["height"]
        font_path = subtitle_font() if voiced else None
        if voiced and not font_path:
            raise RuntimeError(
                "No CJK subtitle font found; configure a local CJK font in the script"
            )
        font = (
            ImageFont.truetype(font_path, max(16, round(width * 0.031)))
            if voiced
            else None
        )
        blank = cards / "blank.png"
        Image.new("RGBA", (width, height)).save(blank)
        concat = []
        cursor = 0

        def append_image(path, duration):
            if duration > 0:
                concat.extend(
                    [concat_line(path.relative_to(ROOT)), f"duration {duration:.6f}"]
                )

        for j, (x, y, text) in enumerate(cues):
            append_image(blank, x - cursor)
            im = Image.new("RGBA", (width, height))
            draw = ImageDraw.Draw(im)
            draw.text(
                (width / 2, height * 0.96),
                text,
                font=font,
                fill="white",
                anchor="mb",
                stroke_width=2,
                stroke_fill="#101B2B",
            )
            path = cards / f"{j:03d}.png"
            im.save(path)
            append_image(path, y - x)
            cursor = y
        append_image(blank, offset - cursor)
        concat.append(concat_line(blank.relative_to(ROOT)))
        (ROOT / "subtitle_concat.txt").write_text(
            "\n".join(concat) + "\n", encoding="utf-8"
        )
    if voiced:
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                "video_clean.mp4",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                "subtitle_concat.txt",
                "-filter_complex",
                "[0:v][1:v]overlay=0:0:eof_action=pass:format=auto[v]",
                "-map",
                "[v]",
                "-map",
                "0:a:0",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "19",
                "-preset",
                "fast",
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                "video.mp4",
            ]
        )
    if not voiced:
        shutil.copyfile(ROOT / "video_clean.mp4", ROOT / "video.mp4")
    result = probe(ROOT / "video.mp4")
    v = next(s for s in result["streams"] if s["codec_type"] == "video")
    audio = next((s for s in result["streams"] if s["codec_type"] == "audio"), None)
    if (v["width"], v["height"]) != (cfg["width"], cfg["height"]) or Fraction(
        v["r_frame_rate"]
    ) != cfg["fps"]:
        raise ValueError("Final video dimensions or frame rate mismatch")
    if abs(float(result["format"]["duration"]) - offset) > max(0.2, 3 / cfg["fps"]):
        raise ValueError("Final video duration drift")
    assert (audio and audio["codec_name"] == "aac") if voiced else audio is None
    run(["ffmpeg", "-v", "error", "-i", "video.mp4", "-f", "null", "-"])
    (ROOT / "chapters.json").write_text(json.dumps(chapters, indent=2))
    (ROOT / "verification.json").write_text(
        json.dumps(
            {
                "video": result,
                "total_scene_duration": offset,
                "subtitle_cues": len(cues),
                "decoded_without_errors": True,
                "script_sha256": source_hash,
                "scene_sources": {s: records[s]["source_sha256"] for s in scenes},
                "subtitle_timing": "estimated by phrase length; not forced alignment",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(
        f"VIDEO_READY {ROOT}/video.mp4; {offset:.2f}s; {len(cues)} subtitle cues",
        flush=True,
    )
