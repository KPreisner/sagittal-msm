# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Draw the explanatory (non-data) figures in docs/figures/.

- slicing.png   the scalar bit matrix, cut the Pippenger way and the Sagittal way
- pippenger.png the Pippenger panel alone
- ec_add.png    adding and doubling points on y^2 = x^3 + 1 drawn over the real numbers
- limbs.png     a 377-bit field multiplication as 32-bit word products

Usage: uv run python scripts/make_figures.py
"""

import argparse
import random
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.axes import Axes

# Dataviz reference palette tokens (light mode). Text never wears a series color.
SAGITTAL = "#2a78d6"
PIPPENGER = "#eb6834"
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
CURVE = "#8a8983"
RESULT = "#1baf7a"

ROWS, BITS = 8, 12
WINDOW, BATCH = 4, 4


TITLES = {
    "pippenger": "Pippenger: strips c bits wide, n rows tall",
    "sagittal": "Sagittal: blocks 1 bit wide, g rows tall",
}


def slicing(path: Path, panels: tuple[str, ...] = ("pippenger", "sagittal")) -> None:
    """The scalar bit matrix sliced one way per panel ("pippenger", "sagittal")."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle

    rng = random.Random(7)
    bits = [[rng.randrange(2) for _ in range(BITS)] for _ in range(ROWS)]

    fig, grid = plt.subplots(
        1, len(panels), figsize=(5.5 * len(panels), 4.6), dpi=150, facecolor=SURFACE, squeeze=False
    )
    axes = dict(zip(panels, grid[0], strict=True))
    for name, ax in axes.items():
        title = TITLES[name]
        ax.set_facecolor(SURFACE)
        ax.set_xlim(-2.2, BITS + 0.8)
        ax.set_ylim(ROWS + 2.3, -1.3)
        ax.axis("off")
        ax.set_title(title, fontsize=11, color=TEXT_PRIMARY, loc="left")
        for col in range(BITS):
            ax.text(
                col + 0.5,
                -0.45,
                str(BITS - 1 - col),
                ha="center",
                va="center",
                fontsize=7,
                color=TEXT_SECONDARY,
            )
        ax.text(-0.15, -0.45, "bit", ha="right", va="center", fontsize=7, color=TEXT_SECONDARY)
        for row in range(ROWS):
            ax.text(
                -0.15,
                row + 0.5,
                f"k{row + 1}·P{row + 1}",
                ha="right",
                va="center",
                fontsize=8,
                color=TEXT_SECONDARY,
            )
            for col in range(BITS):
                ax.add_patch(
                    Rectangle((col, row), 1, 1, facecolor=SURFACE, edgecolor=GRID, linewidth=0.8)
                )
                ax.text(
                    col + 0.5,
                    row + 0.5,
                    str(bits[row][col]),
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=TEXT_PRIMARY,
                )

    def outline(
        ax: "Axes", x: float, y: float, w: float, h: float, color: str, strong: bool
    ) -> None:
        """Faint outline for every slice; a filled, heavy outline for the highlighted one."""
        box = FancyBboxPatch(
            (x + 0.06, y + 0.06),
            w - 0.12,
            h - 0.12,
            boxstyle="round,pad=0,rounding_size=0.15",
            facecolor=color if strong else "none",
            alpha=0.28 if strong else 0.6,
            edgecolor=color,
            linewidth=2.2 if strong else 0.7,
        )
        ax.add_patch(box)

    if "pippenger" in axes:
        left = axes["pippenger"]
        # Pippenger: every window spans all rows; one is highlighted.
        for w in range(BITS // WINDOW):
            outline(left, w * WINDOW, 0, WINDOW, ROWS, PIPPENGER, w == 1)
        digit = "".join(str(b) for b in bits[2][WINDOW : 2 * WINDOW])
        left.text(
            0,
            ROWS + 0.9,
            f"Each row's {WINDOW}-bit digit picks a bucket: "
            f"row 3 → bucket {int(digit, 2)} ({digit}).",
            fontsize=8.5,
            color=TEXT_PRIMARY,
        )
        left.text(
            0,
            ROWS + 1.7,
            f"$2^{WINDOW} - 1$ buckets per window, filled by the scalars; then a bucket reduction.",
            fontsize=8.5,
            color=TEXT_SECONDARY,
        )

    if "sagittal" in axes:
        right = axes["sagittal"]
        # Sagittal: every (bit, batch) block is 1 x g; one is highlighted.
        for batch in range(ROWS // BATCH):
            for col in range(BITS):
                highlight = batch == 0 and col == 4
                outline(right, col, batch * BATCH, 1, BATCH, SAGITTAL, highlight)
        chosen = " + ".join(f"P{r + 1}" for r in range(BATCH) if bits[r][4])
        right.plot([0, BITS], [BATCH, BATCH], color=TEXT_SECONDARY, linewidth=1.2)  # batch boundary
        right.text(
            BITS + 0.15,
            BATCH / 2,
            "batch 1",
            rotation=90,
            va="center",
            fontsize=7,
            color=TEXT_SECONDARY,
        )
        right.text(
            BITS + 0.15,
            BATCH * 1.5,
            "batch 2",
            rotation=90,
            va="center",
            fontsize=7,
            color=TEXT_SECONDARY,
        )
        right.text(
            0,
            ROWS + 0.9,
            f"Bit {BITS - 1 - 4} of k1..k{BATCH} selects one precomputed subset sum: {chosen}.",
            fontsize=8.5,
            color=TEXT_PRIMARY,
        )
        right.text(
            0,
            ROWS + 1.7,
            f"It is added to the bucket for bit {BITS - 1 - 4}: one bucket per bit, no reduction.",
            fontsize=8.5,
            color=TEXT_SECONDARY,
        )

    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def curve_y(x: float) -> float:
    """Upper branch of y^2 = x^3 + 1 over the reals (x >= -1)."""
    return float(max(x**3 + 1, 0.0) ** 0.5)


def chord(p: tuple[float, float], q: tuple[float, float]) -> tuple[float, tuple[float, float]]:
    """Slope of the line through p and q (tangent if equal), and the sum p + q."""
    (x1, y1), (x2, y2) = p, q
    lam = 3 * x1 * x1 / (2 * y1) if p == q else (y2 - y1) / (x2 - x1)
    x3 = lam * lam - x1 - x2
    return lam, (x3, lam * (x1 - x3) - y1)


def draw_curve(ax: "Axes") -> None:
    import numpy as np

    xs = np.linspace(-1, 2.2, 600)
    ys = np.sqrt(np.maximum(xs**3 + 1, 0))
    for sign in (1, -1):
        ax.plot(xs, sign * ys, color=CURVE, linewidth=1.6)
    ax.axhline(0, color=GRID, linewidth=0.8, zorder=0)
    ax.set_xlim(-1.6, 2.4)
    ax.set_ylim(-3.6, 3.6)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)


def mark(
    ax: "Axes",
    pt: tuple[float, float],
    label: str,
    color: str,
    dx: float = 0.1,
    dy: float = 0.15,
    hollow: bool = False,
) -> None:
    ax.plot(
        *pt,
        "o",
        markersize=8,
        color=color,
        markerfacecolor=SURFACE if hollow else color,
        markeredgewidth=1.8,
        zorder=5,
    )
    ax.text(pt[0] + dx, pt[1] + dy, label, fontsize=11, color=TEXT_PRIMARY, zorder=6)


def ec_add(path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), dpi=150, facecolor=SURFACE)
    p, q = (-0.8, curve_y(-0.8)), (1.5, curve_y(1.5))
    for ax, (title, a, b) in zip(
        axes, [("Adding: P + Q", p, q), ("Doubling: P + P = 2P", q, q)], strict=True
    ):
        ax.set_facecolor(SURFACE)
        draw_curve(ax)
        lam, s = chord(a, b)
        third = (s[0], -s[1])
        xs = [min(a[0], third[0]) - 0.4, max(b[0], third[0]) + 0.4]
        ax.plot(xs, [a[1] + lam * (x - a[0]) for x in xs], color=SAGITTAL, linewidth=1.6)
        ax.plot(
            [third[0], s[0]], [third[1], s[1]], color=TEXT_SECONDARY, linewidth=1.2, linestyle="--"
        )
        if a == b:
            mark(ax, a, "P", TEXT_PRIMARY, dx=0.12, dy=-0.45)
        else:
            mark(ax, a, "P", TEXT_PRIMARY, dx=-0.3, dy=0.2)
            mark(ax, b, "Q", TEXT_PRIMARY, dx=0.12, dy=-0.1)
        mark(ax, third, "", TEXT_SECONDARY, hollow=True)
        mark(ax, s, "2P" if a == b else "P + Q", RESULT, dx=0.12, dy=-0.4)
        ax.set_title(title, fontsize=12, loc="left", color=TEXT_PRIMARY)
        how = (
            "tangent at P meets the curve again;"
            if a == b
            else "the line through P and Q meets the curve again;"
        )
        ax.text(
            -1.55,
            -3.45,
            how + "\nreflect that point across the x-axis",
            fontsize=9,
            color=TEXT_SECONDARY,
        )
    fig.suptitle(
        "$y^2 = x^3 + 1$ over the real numbers (BLS12-377 uses this equation mod a 377-bit prime)",
        fontsize=10,
        color=TEXT_SECONDARY,
        x=0.01,
        ha="left",
    )
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def limbs(path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    words = 12  # 377 bits in 32-bit words
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axis("off")
    size = 0.38
    left, top = 1.4, 0.0
    for name, y in (("a", top), ("b", top - 0.55)):
        ax.text(
            left - 0.25,
            y + size / 2,
            name,
            ha="right",
            va="center",
            fontsize=12,
            color=TEXT_PRIMARY,
        )
        for i in range(words):
            ax.add_patch(
                Rectangle(
                    (left + i * size, y),
                    size * 0.92,
                    size * 0.92,
                    facecolor=SAGITTAL,
                    alpha=0.25,
                    edgecolor=SAGITTAL,
                )
            )
        ax.text(
            left + words * size + 0.15,
            y + size / 2,
            "12 words of 32 bits (377 bits used)",
            va="center",
            fontsize=9,
            color=TEXT_SECONDARY,
        )
    grid_top = top - 1.4
    ax.text(
        left - 0.25,
        grid_top - words * size / 2,
        "a × b",
        ha="right",
        va="center",
        fontsize=12,
        color=TEXT_PRIMARY,
    )
    for i in range(words):
        for j in range(words):
            ax.add_patch(
                Rectangle(
                    (left + j * size, grid_top - (i + 1) * size),
                    size * 0.92,
                    size * 0.92,
                    facecolor=PIPPENGER,
                    alpha=0.22,
                    edgecolor=PIPPENGER,
                    linewidth=0.6,
                )
            )
    notes = [
        ("144 word multiplications for the product a × b", TEXT_PRIMARY),
        (
            "+ about 156 more to reduce it mod p (Montgomery, CIOS: 2s² + s = 300 for s = 12)",
            TEXT_PRIMARY,
        ),
        (
            "≈ 300 multiply-adds per field multiplication, with a carry chain through every one",
            TEXT_SECONDARY,
        ),
        ("× 10 field multiplications per mixed add ≈ 3,000 per curve addition", TEXT_SECONDARY),
        ("", TEXT_SECONDARY),
        (
            "Each orange cell is one 32 × 32 → 64-bit multiply of a word of a by a word of b.",
            TEXT_SECONDARY,
        ),
        (
            "A 64-bit CPU needs 6 × 6 = 36 for the product; GPUs multiply 32 bits at a time.",
            TEXT_SECONDARY,
        ),
    ]
    for k, (note, color) in enumerate(notes):
        ax.text(
            left + words * size + 0.3, grid_top - 0.5 - k * 0.55, note, fontsize=10, color=color
        )
    ax.set_xlim(0, 13)
    ax.set_ylim(grid_top - words * size - 0.3, top + 0.8)
    ax.set_title(
        "One 377-bit field multiplication on a GPU with 32-bit integer multipliers",
        fontsize=12,
        loc="left",
        color=TEXT_PRIMARY,
    )
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).parent.parent / "docs" / "figures"
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    slicing(args.out / "slicing.png")
    slicing(args.out / "pippenger.png", ("pippenger",))
    ec_add(args.out / "ec_add.png")
    limbs(args.out / "limbs.png")
    print(f"Wrote slicing.png, pippenger.png, ec_add.png and limbs.png to {args.out}")


if __name__ == "__main__":
    main()
