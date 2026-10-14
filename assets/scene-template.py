"""Executable starting point. Replace Scene01's visual content for the request."""

from manim import *
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
DATA = json.loads((ROOT / "timestamps.json").read_text(encoding="utf-8"))
config.pixel_width = CFG["width"]
config.pixel_height = CFG["height"]
config.frame_width = CFG["frame_width"]
config.frame_height = CFG["frame_height"]
config.frame_rate = CFG["fps"]
config.background_color = "#101B2B"


class NarratedScene(Scene):
    def begin(self, i):
        d = DATA[i]
        start = self.time
        if d["audio"]:
            self.add_sound(d["audio"])
        return d["duration_s"], start

    def finish(self, budget, start):
        used = self.time - start
        if used > budget + 1 / config.frame_rate:
            raise ValueError("Animation exceeds segment duration budget")
        if budget > used:
            self.wait(budget - used)


class Scene01(NarratedScene):
    def construct(self):
        budget, start = self.begin(0)
        # Minimal renderable example; replace this with explanatory mathematical motion.
        circle = Circle(
            radius=min(config.frame_width, config.frame_height) * 0.20, color=TEAL
        )
        formula = MathTex(r"\sin^2\alpha+\cos^2\alpha=1", font_size=32)
        formula.scale_to_fit_width(min(formula.width, config.frame_width * 0.86))
        formula.next_to(circle, DOWN, buff=0.4)
        self.play(Create(circle), run_time=min(1, budget * 0.2))
        self.play(Write(formula), run_time=min(1, budget * 0.2))
        self.finish(budget, start)
