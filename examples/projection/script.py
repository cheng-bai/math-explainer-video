"""Original projection lesson. Geometry and labels share one angle tracker."""

from manim import *
import manimpango
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
DATA = (
    json.loads((ROOT / "timestamps.json").read_text(encoding="utf-8"))
    if (ROOT / "timestamps.json").exists()
    else []
)
config.pixel_width = CFG["width"]
config.pixel_height = CFG["height"]
config.frame_width = CFG["frame_width"]
config.frame_height = CFG["frame_height"]
config.frame_rate = CFG["fps"]
config.background_color = "#101B2B"
INK, ACC, BLUE, GOLD, MUT = WHITE, "#59D9C0", "#75ACFF", "#FFC66D", "#9FAEC3"
FONTS = set(manimpango.list_fonts())
FONT = os.environ.get("MATH_VIDEO_FONT_FAMILY") or next(
    (
        f
        for f in (
            "PingFang SC",
            "Noto Sans CJK SC",
            "Microsoft YaHei",
            "Hiragino Sans GB",
        )
        if f in FONTS
    ),
    None,
)
if not FONT or FONT not in FONTS:
    raise RuntimeError("Set MATH_VIDEO_FONT_FAMILY to an installed Chinese font family")


def text(value, size=27, color=INK):
    return Text(value, font=FONT, font_size=size, color=color)


def formula(value, y, size=36, color=INK):
    mob = MathTex(value, font_size=size, color=color)
    if mob.width > 6.9:
        mob.scale_to_fit_width(6.9)
    return mob.move_to([3.9, y, 0])


class ProjectionBoard(Scene):
    def header(self, title, previous, following):
        self.add(text(title, 35).move_to([0, 3.65, 0]))
        self.add(text("依据：" + previous, 21, MUT).move_to([-3.8, 2.9, 0]))
        self.add(text("下一步：" + following, 21, GOLD).move_to([3.8, 2.9, 0]))
        self.add(Line([0.1, -2.8, 0], [0.1, 2.4, 0], color="#40566E"))
        self.add(
            text("原创示例 · 投影、数量积与垂直条件", 19, MUT).move_to([0, -3.35, 0])
        )

    def model(self, degrees):
        # Identical unit length: 6 units across, 4 units vertically.
        unit = 1.08
        axes = Axes(
            x_range=[-2, 4, 1],
            y_range=[-1, 3, 1],
            x_length=6 * unit,
            y_length=4 * unit,
            tips=False,
            axis_config={"color": "#566981", "stroke_width": 2},
        ).move_to([-3.9, -0.1, 0])
        theta = ValueTracker(degrees * DEGREES)
        origin = axes.c2p(0, 0)
        endpoint = lambda: axes.c2p(
            2 * np.cos(theta.get_value()), 2 * np.sin(theta.get_value())
        )
        foot = lambda: axes.c2p(2 * np.cos(theta.get_value()), 0)

        def projection():
            if abs(np.cos(theta.get_value())) < 0.005:
                return Dot(origin, color=GOLD, radius=0.065)
            return Arrow(origin, foot(), buff=0, color=GOLD, stroke_width=5)

        self.add(
            axes, Arrow(origin, axes.c2p(3, 0), buff=0, color=BLUE, stroke_width=5)
        )
        self.add(
            always_redraw(
                lambda: Arrow(origin, endpoint(), buff=0, color=ACC, stroke_width=5)
            )
        )
        self.add(always_redraw(lambda: DashedLine(endpoint(), foot(), color=MUT)))
        self.add(always_redraw(projection))
        self.add(
            always_redraw(
                lambda: Arc(
                    radius=0.55, angle=theta.get_value(), arc_center=origin, color=ACC
                )
            )
        )
        self.add(
            always_redraw(
                lambda: text(
                    "O=H" if abs(np.cos(theta.get_value())) < 0.005 else "O", 24, MUT
                ).move_to(origin + LEFT * 0.28 + DOWN * 0.3)
            )
        )
        self.add(text("a", 28, BLUE).next_to(axes.c2p(3, 0), DOWN))
        self.add(always_redraw(lambda: text("b", 28, ACC).next_to(endpoint(), UP)))
        self.add(
            always_redraw(
                lambda: (
                    VGroup()
                    if abs(np.cos(theta.get_value())) < 0.005
                    else text("H", 26, GOLD).next_to(foot(), DOWN)
                )
            )
        )
        self.add(
            always_redraw(
                lambda: (
                    VGroup(
                        text("夹角", 25),
                        DecimalNumber(
                            theta.get_value() / DEGREES,
                            num_decimal_places=0,
                            unit=r"^\circ",
                            font_size=30,
                        ),
                    )
                    .arrange(RIGHT)
                    .move_to([-3.8, -2.6, 0])
                )
            )
        )
        self.add(formula(r"\mathbf a=(3,0),\quad|\mathbf b|=2", 2, 33))
        return theta

    def projection_formula(self):
        self.add(formula(r"s=2\cos\theta", 0.9, 40, GOLD))
        self.add(text("数量投影可以带符号，长度非负", 26, GOLD).move_to([3.9, -0.1, 0]))

    def begin(self, index):
        entry = DATA[index]
        if entry["audio"]:
            self.add_sound(entry["audio"])
        return entry["duration_s"]

    def at_phrase(self, index, phrase):
        entry = DATA[index]
        position = entry["text"].find(phrase)
        if position < 0:
            raise ValueError("Narration phrase missing: " + phrase)
        duration = entry["audio_duration"] or entry["duration_s"]
        target = duration * position / len(entry["text"])
        if target > self.time:
            self.wait(target - self.time, frozen_frame=True)

    def finish(self, budget):
        if self.time > budget + 1 / config.frame_rate:
            raise ValueError("Animation exceeds segment budget")
        if self.time < budget:
            self.wait(budget - self.time, frozen_frame=True)


class Scene01(ProjectionBoard):
    def construct(self):
        budget = self.begin(0)
        self.header(
            "沿一个方向，读取另一个向量的贡献",
            "参考向量 a 非零",
            "角度改变，投影如何变化",
        )
        self.model(30)
        self.play(
            Write(formula(r"\overrightarrow{OH}=(2\cos\theta,0)", 0.9, 34, GOLD)),
            run_time=1.5,
        )
        self.play(Write(formula(r"s=2\cos\theta", -0.3, 40, GOLD)), run_time=1.2)
        self.add(text("投影向量是箭头，数量投影是数", 25).move_to([3.9, -1.6, 0]))
        self.finish(budget)


class Scene02(ProjectionBoard):
    def construct(self):
        budget = self.begin(1)
        self.header("只改变角度：同向 → 零 → 反向", "保留 s=2cosθ", "将贡献变为数量积")
        theta = self.model(30)
        self.projection_formula()
        self.add(
            always_redraw(
                lambda: DecimalNumber(
                    2 * np.cos(theta.get_value()),
                    num_decimal_places=2,
                    font_size=43,
                    color=GOLD,
                ).move_to([3.9, -1.3, 0])
            )
        )
        self.at_phrase(1, "转到九十度")
        self.play(theta.animate.set_value(90 * DEGREES), run_time=1)
        self.at_phrase(1, "继续转到")
        self.play(theta.animate.set_value(130 * DEGREES), run_time=1)
        self.finish(budget)


class Scene03(ProjectionBoard):
    def construct(self):
        budget = self.begin(2)
        self.header(
            "数量积：把贡献与垂直关系连接起来", "数量投影 s=2cosθ", "检查非零条件"
        )
        theta = self.model(130)
        self.add(formula(r"\mathbf a\cdot\mathbf b=|\mathbf a|s=6\cos\theta", 0.9, 34))
        self.at_phrase(2, "再转回九十度")
        self.play(theta.animate.set_value(90 * DEGREES), run_time=1)
        self.at_phrase(2, "因此")
        self.play(
            Write(
                formula(
                    r"\mathbf a,\mathbf b\ne\mathbf0:\quad\mathbf a\cdot\mathbf b=0\iff\mathbf a\perp\mathbf b",
                    -0.3,
                    28,
                    ACC,
                )
            ),
            run_time=1.5,
        )
        self.at_phrase(2, "非零条件不能省略")
        self.add(
            text("零向量点乘为0，但没有确定方向", 25, GOLD).move_to([3.9, -1.7, 0])
        )
        self.finish(budget)


class OverviewScene(ProjectionBoard):
    def construct(self):
        self.header(
            "投影 → 数量积 → 垂直：推导全貌",
            "a、b 均非零，夹角 θ∈[0,π]",
            "用条件解释结论",
        )
        self.model(130)
        self.add(formula(r"s=|\mathbf b|\cos\theta=2\cos\theta", 1.1, 32, GOLD))
        self.add(formula(r"\mathbf a\cdot\mathbf b=|\mathbf a|s=6\cos\theta", 0.1, 32))
        self.add(
            formula(
                r"\mathbf a\cdot\mathbf b=0\iff\theta=\frac\pi2\iff\mathbf a\perp\mathbf b",
                -1.1,
                29,
                ACC,
            )
        )
        self.add(
            text("数量投影带符号；零向量另行规定点乘为0", 23, GOLD).move_to(
                [3.9, -2.2, 0]
            )
        )
