# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Render the README animations in docs/figures/.

- ec_add.gif     adding two points on y^2 = x^3 + 1, one step at a time
- tables.gif     building Sagittal's precomputed tables: every combination of each batch's points,
                 one addition per entry
- sagittal.gif   Sagittal's accumulation: each 1 x g block of bits adds one table entry to the
                 bucket for its bit

Usage: uv run python scripts/make_animations.py
"""

import argparse
import random
from collections.abc import Callable
from pathlib import Path

from make_figures import (
    GRID,
    RESULT,
    SAGITTAL,
    SURFACE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    chord,
    curve_y,
    draw_curve,
    mark,
)

FPS = 2


def save(path: Path, fig: object, draw: Callable[[int], None], frames: list[int]) -> None:
    """Render `draw(stage)` for each entry of `frames` (repeat a stage to hold it longer)."""
    from matplotlib.animation import FuncAnimation, PillowWriter

    animation = FuncAnimation(fig, lambda i: draw(frames[i]), frames=len(frames))  # type: ignore[arg-type]
    animation.save(path, writer=PillowWriter(fps=FPS), savefig_kwargs={"facecolor": SURFACE})


def ec_add(path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4.2), dpi=90, facecolor=SURFACE)
    p, q = (-0.8, curve_y(-0.8)), (1.5, curve_y(1.5))
    lam, s = chord(p, q)
    third = (s[0], -s[1])
    captions = [
        "An elliptic curve: y² = x³ + 1",
        "Take a point P on the curve",
        "and a second point Q",
        "Draw the line through P and Q",
        "It meets the curve at exactly one more point",
        "Reflect that point across the x-axis",
        "That point is P + Q. In coordinates: λ = (y₂ − y₁)/(x₂ − x₁),\n"
        "x₃ = λ² − x₁ − x₂,  y₃ = λ(x₁ − x₃) − y₁",
    ]

    def draw(stage: int) -> None:
        ax.cla()
        ax.set_facecolor(SURFACE)
        draw_curve(ax)
        if stage >= 1:
            mark(ax, p, "P", TEXT_PRIMARY, dx=-0.3, dy=0.2)
        if stage >= 2:
            mark(ax, q, "Q", TEXT_PRIMARY, dx=0.12, dy=-0.1)
        if stage >= 3:
            xs = [p[0] - 0.4, q[0] + 0.4]
            ax.plot(xs, [p[1] + lam * (x - p[0]) for x in xs], color=SAGITTAL, linewidth=1.8)
        if stage >= 4:
            mark(ax, third, "", TEXT_SECONDARY, hollow=True)
        if stage >= 5:
            ax.plot(
                [third[0], s[0]],
                [third[1], s[1]],
                color=TEXT_SECONDARY,
                linewidth=1.2,
                linestyle="--",
            )
        if stage >= 6:
            mark(ax, s, "P + Q", RESULT, dx=0.12, dy=-0.4)
        ax.text(-1.55, -3.45, captions[stage], fontsize=10, color=TEXT_PRIMARY, va="bottom")

    fig.tight_layout()
    frames = [stage for stage in range(7) for _ in range(5 if stage == 6 else 3)]
    save(path, fig, draw, frames)
    plt.close(fig)


def sagittal(path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    rows, bits, g = 8, 8, 4
    rng = random.Random(3)
    matrix = [[rng.randrange(2) for _ in range(bits)] for _ in range(rows)]
    steps = [(batch, col) for batch in range(rows // g) for col in range(bits)]

    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=90, facecolor=SURFACE)

    def subset(batch: int, col: int) -> list[int]:
        return [batch * g + t + 1 for t in range(g) if matrix[batch * g + t][col]]

    def draw(step: int) -> None:
        ax.cla()
        ax.set_facecolor(SURFACE)
        ax.axis("off")
        ax.set_xlim(-1.8, 22)
        ax.set_ylim(rows + 2.6, -1.6)
        for col in range(bits):
            ax.text(
                col + 0.5, -0.5, str(bits - 1 - col), ha="center", fontsize=8, color=TEXT_SECONDARY
            )
        ax.text(-0.2, -0.5, "bit", ha="right", fontsize=8, color=TEXT_SECONDARY)
        for r in range(rows):
            ax.text(
                -0.2,
                r + 0.5,
                f"k{r + 1}",
                ha="right",
                va="center",
                fontsize=9,
                color=TEXT_SECONDARY,
            )
            for col in range(bits):
                ax.add_patch(Rectangle((col, r), 1, 1, facecolor=SURFACE, edgecolor=GRID))
                ax.text(
                    col + 0.5,
                    r + 0.5,
                    str(matrix[r][col]),
                    ha="center",
                    va="center",
                    fontsize=10,
                    color=TEXT_PRIMARY,
                )
        ax.plot([0, bits], [g, g], color=TEXT_SECONDARY, linewidth=1.2)

        # Buckets: one per bit, filled by the steps done so far.
        done = steps[: step + 1] if step < len(steps) else steps
        ax.text(10, -0.5, "bucket", fontsize=8, color=TEXT_SECONDARY)
        for i, col in enumerate(range(bits)):
            terms = [
                "+".join(f"P{j}" for j in subset(b, c))
                for b, c in done
                if c == col and subset(b, c)
            ]
            ax.text(
                10, i + 0.5, f"bit {bits - 1 - col}", va="center", fontsize=9, color=TEXT_SECONDARY
            )
            ax.text(
                12,
                i + 0.5,
                " + ".join(f"({t})" for t in terms),
                va="center",
                fontsize=9,
                color=TEXT_PRIMARY,
            )

        if step < len(steps):
            batch, col = steps[step]
            ax.add_patch(
                Rectangle(
                    (col + 0.06, batch * g + 0.06),
                    0.88,
                    g - 0.12,
                    facecolor=SAGITTAL,
                    alpha=0.3,
                    edgecolor=SAGITTAL,
                    linewidth=2,
                )
            )
            ax.add_patch(
                Rectangle(
                    (9.8, col + 0.1), 12, 0.8, facecolor=SAGITTAL, alpha=0.1, edgecolor="none"
                )
            )
            pattern = "".join(str(matrix[batch * g + t][col]) for t in range(g))
            chosen = " + ".join(f"P{j}" for j in subset(batch, col)) or "nothing (all zeros)"
            caption = (
                f"Batch {batch + 1}, bit {bits - 1 - col}: bits {pattern} → table entry "
                f"{chosen} → bucket for bit {bits - 1 - col}"
            )
        else:
            caption = (
                f"Every block done: {bits} buckets, one per bit. Combine them with "
                f"{bits - 1} doublings: result = 2(…2(2·b7 + b6)…) + b0"
            )
        ax.text(-1.6, rows + 1.2, caption, fontsize=10, color=TEXT_PRIMARY)
        ax.text(
            -1.6,
            rows + 2.1,
            f"g = {g}: each batch's $2^{{{g}}} - 1$ subset sums are "
            "precomputed once; every proof only looks them up.",
            fontsize=9,
            color=TEXT_SECONDARY,
        )

    fig.tight_layout()
    frames = [step for step in range(len(steps)) for _ in range(2)] + [len(steps)] * 6
    save(path, fig, draw, frames)
    plt.close(fig)


def tables(path: Path) -> None:
    """Build both batches' tables for the points of sagittal.gif (g = 4: P1..P4 and P5..P8)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    g = 4
    size = (1 << g) - 1  # nonempty subsets of a batch

    def members(mask: int, batch: int) -> list[int]:
        return [batch * g + t + 1 for t in range(g) if mask >> t & 1]

    def label(mask: int, batch: int) -> str:
        return " + ".join(f"P{j}" for j in members(mask, batch))

    def pattern(mask: int) -> str:
        """Bits in point order, as sagittal.gif prints them (first character = first point)."""
        return "".join(str(mask >> t & 1) for t in range(g))

    # Slot c holds mask c + 1. d = c & (c + 1) splits it into slots c - d and d - 1.
    sources = []
    for c in range(size):
        d = c & (c + 1)
        sources.append((c - d, d - 1) if d else None)

    fig, ax = plt.subplots(figsize=(9, 5.6), dpi=90, facecolor=SURFACE)
    top = 1.6  # rows start below the header

    def draw(step: int) -> None:
        ax.cla()
        ax.set_facecolor(SURFACE)
        ax.axis("off")
        ax.set_xlim(0, 20)
        ax.set_ylim(top + size + 2.4, -1.1)
        ax.text(
            0.2,
            -0.35,
            f"One table per batch, holding every combination of that batch's "
            f"{g} points: 2 batches, so 2 tables.",
            fontsize=10,
            color=TEXT_PRIMARY,
        )
        header = [
            (0.2, "bits"),
            (2.4, "batch 1 table (P1..P4)"),
            (8.0, "batch 2 table (P5..P8)"),
            (13.4, "built as (batch 1; batch 2 the same)"),
        ]
        for x, text in header:
            ax.text(x, top - 0.7, text, fontsize=9, color=TEXT_SECONDARY)
        building = step if step < size else None
        pair = sources[building] if building is not None else None
        if pair is not None:
            for s in pair:  # the two entries being added
                ax.add_patch(
                    Rectangle((0, top + s), 20, 0.9, facecolor=RESULT, alpha=0.15, edgecolor="none")
                )
        if building is not None:
            ax.add_patch(
                Rectangle(
                    (0, top + building), 20, 0.9, facecolor=SAGITTAL, alpha=0.25, edgecolor="none"
                )
            )
        additions = 0
        for c in range(size):
            mask, y = c + 1, top + c + 0.45
            done = c <= step
            ax.text(
                0.2,
                y,
                pattern(mask),
                va="center",
                fontsize=10,
                family="monospace",
                color=TEXT_PRIMARY if done else GRID,
            )
            if not done:
                continue
            ax.text(2.4, y, label(mask, 0), va="center", fontsize=10, color=TEXT_PRIMARY)
            ax.text(8.0, y, label(mask, 1), va="center", fontsize=10, color=TEXT_PRIMARY)
            source = sources[c]
            if source is not None:
                a, b = source
                how = f"({label(a + 1, 0)}) + ({label(b + 1, 0)})"
                additions += 1
            else:
                how = "input point, no addition"
            ax.text(13.4, y, how, va="center", fontsize=9, color=TEXT_SECONDARY)
        if building is not None:
            caption = (
                f"Entry {building + 1} of {size}: additions so far {additions} per batch. "
                "Each new entry adds two entries built earlier."
            )
        else:
            caption = (
                f"All {size} combinations of each batch's {g} points, {size - g} additions "
                "per batch. n points need n/g tables."
            )
        ax.text(0.2, top + size + 0.9, caption, fontsize=10, color=TEXT_PRIMARY)
        ax.text(
            0.2,
            top + size + 1.8,
            "Combinations, not permutations: P1 + P2 = P2 + P1, so "
            f"there are $2^{{{g}}} - 1 = {size}$ nonempty subsets. Built once per proving key.",
            fontsize=9,
            color=TEXT_SECONDARY,
        )

    fig.tight_layout()
    frames = [step for step in range(size) for _ in range(2)] + [size] * 6
    save(path, fig, draw, frames)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).parent.parent / "docs" / "figures"
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    ec_add(args.out / "ec_add.gif")
    tables(args.out / "tables.gif")
    sagittal(args.out / "sagittal.gif")
    print(f"Wrote ec_add.gif, tables.gif and sagittal.gif to {args.out}")


if __name__ == "__main__":
    main()
