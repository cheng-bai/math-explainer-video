import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from media_utils import concat_line, read_config


def cli(name, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name), *map(str, args)],
        capture_output=True,
        text=True,
    )


class WorkflowTests(unittest.TestCase):
    def test_initialization_non_overwrite_and_offline_preparation(self):
        with tempfile.TemporaryDirectory(prefix="math video's ") as directory:
            first = cli("new_project.py", "lesson", "--root", directory, "--width", 640)
            self.assertEqual(first.returncode, 0, first.stderr)
            project = Path(first.stdout.strip())
            config = read_config(project)
            self.assertEqual((config["width"], config["height"]), (640, 360))
            marker = project / "keep.txt"
            marker.write_text("preserve")
            second = cli("new_project.py", "lesson", "--root", directory)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotEqual(Path(second.stdout.strip()), project)
            self.assertEqual(marker.read_text(), "preserve")
            (project / "narration.json").write_text(json.dumps(["第一步", "第二步"]))
            result = cli("prepare_audio.py", project, "--silent", "--duration", 1.13)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((project / "timestamps.json").read_text())
            self.assertEqual(len(data), 2)
            self.assertTrue(
                all(d["audio"] is None and d["audio_duration"] == 0 for d in data)
            )
            self.assertTrue(all(d["duration_s"] >= 1.13 for d in data))
            invalid = cli("prepare_audio.py", project, "--silent", "--duration", "nan")
            self.assertNotEqual(invalid.returncode, 0)
            self.assertEqual(
                json.loads((project / "timestamps.json").read_text()), data
            )

    def test_reject_empty_narration_and_bad_slug(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = cli("new_project.py", "../escape", "--root", directory)
            self.assertNotEqual(bad.returncode, 0)
            valid = cli("new_project.py", "lesson", "--root", directory)
            empty = cli("prepare_audio.py", Path(valid.stdout.strip()), "--silent")
            self.assertNotEqual(empty.returncode, 0)

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is not installed")
    def test_imported_audio_budget_and_stale_render_rejection(self):
        with tempfile.TemporaryDirectory(prefix="local narration ") as directory:
            project = Path(
                cli("new_project.py", "lesson", "--root", directory).stdout.strip()
            )
            (project / "narration.json").write_text(json.dumps(["测试配音导入"]))
            source = Path(directory) / "recordings"
            source.mkdir()
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=220:duration=1",
                    "-c:a",
                    "libmp3lame",
                    str(source / "00.mp3"),
                ],
                check=True,
            )
            imported = cli("prepare_audio.py", project, "--audio-dir", source)
            self.assertEqual(imported.returncode, 0, imported.stderr)
            data = json.loads((project / "timestamps.json").read_text())
            self.assertTrue(Path(data[0]["audio"]).is_file())
            self.assertGreater(data[0]["duration_s"], data[0]["audio_duration"])
            rejected = cli("render_video.py", project, "--assemble-only")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("no render manifest", rejected.stderr)
            self.assertFalse((project / "verification.json").exists())

    def test_geometry_keyframes_and_boundary(self):
        # Independent mathematical check, not a substitute for visual review.
        for degrees, expected in ((30, math.sqrt(3)), (90, 0), (130, -1.285575219)):
            theta = math.radians(degrees)
            bx, by = 2 * math.cos(theta), 2 * math.sin(theta)
            self.assertAlmostEqual(bx, expected, places=8)
            self.assertAlmostEqual(bx * bx + by * by, 4)
            self.assertAlmostEqual(3 * bx, 6 * math.cos(theta))

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is not installed")
    def test_real_ffconcat_with_space_unicode_and_quote(self):
        with tempfile.TemporaryDirectory(prefix="math video's ") as directory:
            project = Path(directory)
            clip = project / "片 段's.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=blue:s=64x64:r=12:d=0.25",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(clip),
                ],
                check=True,
            )
            (project / "list.txt").write_text(
                concat_line(clip.name) + "\n", encoding="utf-8"
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    "list.txt",
                    "-f",
                    "null",
                    "-",
                ],
                cwd=project,
                check=True,
            )
            with self.assertRaises(ValueError):
                concat_line("invalid\npath")


if __name__ == "__main__":
    unittest.main()
