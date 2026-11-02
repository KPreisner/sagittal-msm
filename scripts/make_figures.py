# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Draw the explanatory (non-data) figures in docs/figures/.

- slicing.png   the scalar bit matrix, cut the Pippenger way and the Sagittal way
- pippenger.png the Pippenger panel alone
- ec_add.png    adding and doubling points on y^2 = x^3 + 1 drawn over the real numbers
- limbs.png     a 377-bit field multiplication as 32-bit word products
- primes.png    BLS12-377's sizes: x, r, p and the point count h·r, to scale in bits

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
        "$y^2 = x^3 + 1$ over the real numbers (cryptography uses the same formulas mod a prime)",
        fontsize=10,
        color=TEXT_SECONDARY,
        x=0.01,
        ha="left",
    )
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def limbs(path: Path) -> None:
    """Long multiplication of two 12-word numbers: shifted rows that add up to 24 words."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    words = 12  # 377 bits in 32-bit words
    size = 0.4
    left = 2.0

    def x(col: int) -> float:
        # Column 0 (word 0) is on the right, as in long multiplication on paper.
        return left + (2 * words - 1 - col) * size

    fig, ax = plt.subplots(figsize=(10, 6.4), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axis("off")

    def cell(col: int, y: float, color: str, alpha: float) -> None:
        ax.add_patch(
            Rectangle(
                (x(col), y),
                size * 0.88,
                size * 0.88,
                facecolor=color,
                alpha=alpha,
                edgecolor=color,
                linewidth=0.6,
            )
        )

    def label(col: int, y: float, text: str, color: str = TEXT_PRIMARY) -> None:
        ax.text(
            x(col) - 0.12, y + size * 0.44, text, ha="right", va="center", fontsize=11, color=color
        )

    for name, y in (("a", 0.0), ("b", -0.5)):
        label(words - 1, y, name)
        for i in range(words):
            cell(i, y, SAGITTAL, 0.3)
    ax.text(
        0.1, size * 0.44, "12 words of 32 bits each", va="center", fontsize=10, color=TEXT_SECONDARY
    )

    row_top = -1.2
    for i in range(words):
        y = row_top - i * (size + 0.06)
        label(i + words, y, f"a × b[{i}]", TEXT_SECONDARY)
        for j in range(words + 1):
            cell(i + j, y, PIPPENGER, 0.3)
    bottom = row_top - words * (size + 0.06)
    ax.plot(
        [x(2 * words - 1), x(0) + size * 0.88],
        [bottom + 0.2, bottom + 0.2],
        color=TEXT_SECONDARY,
        linewidth=0.8,
    )
    product = bottom - 0.3
    label(2 * words - 1, product, "24 words")
    for col in range(2 * words):
        cell(col, product, RESULT, 0.4)

    ax.text(
        0.1,
        -0.3,
        "Each row: all 12 words of a\ntimes one word of b. Each\nword product is 64 bits,\n"
        "so a row is 13 words.\n\nEach row starts one word\nfurther left.\n\n12 × 12 = 144 word\n"
        "multiplications. The\ncolumns add up, with\ncarries, to a 24-word\nproduct.",
        va="top",
        fontsize=10,
        color=TEXT_SECONDARY,
        linespacing=1.4,
    )
    ax.set_xlim(0, x(0) + size + 0.1)
    ax.set_ylim(product - 0.2, size + 0.3)
    ax.set_title(
        "Multiplying two 377-bit numbers with 32-bit words: long multiplication",
        fontsize=12,
        loc="left",
        color=TEXT_PRIMARY,
    )
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def primes(path: Path) -> None:
    """BLS12-377's primes to scale in bits, built from its one 64-bit parameter x."""
    import math

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    x = 0x8508C00000000001
    r = x**4 - x**2 + 1
    p = (x - 1) ** 2 * r // 3 + x
    h = (x - 1) ** 2 // 3  # cofactor: the curve has h·r points
    lx, lr, lp, lh = (math.log2(v) for v in (x, r, p, h))

    fig, ax = plt.subplots(figsize=(10, 3.9), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axis("off")
    height, left = 0.55, 0.0

    def bar(y: float, start: float, length: float, color: str, alpha: float = 0.3) -> None:
        ax.add_patch(
            Rectangle((start, y), length, height, facecolor=color, alpha=alpha, edgecolor=color)
        )

    def split(y: float, count: int) -> None:
        """Dividers every log2(x) bits: r is about x^4, p about x^6."""
        for i in range(1, count):
            ax.plot([i * lx] * 2, [y, y + height], color=TEXT_SECONDARY, linewidth=0.8)

    rows = [
        (0, "x", f"{x.bit_length()} bits: the one parameter BLS12-377 is built from"),
        (
            1,
            "r = x⁴ − x² + 1",
            f"{r.bit_length()} bits: the subgroup has r points. Scalars are mod r.",
        ),
        (2, "p ≈ x⁶ / 3", f"{p.bit_length()} bits: the field. Coordinates are mod p."),
        (3, "curve points = h · r", f"h is {h.bit_length()} bits, so the curve has about p points"),
    ]
    for row, label, note in rows:
        y = -row
        ax.text(
            left - 6,
            y + height / 2,
            label,
            ha="right",
            va="center",
            fontsize=11,
            color=TEXT_PRIMARY,
        )
        end = {0: lx, 1: lr, 2: lp, 3: lr + lh}[row]
        ax.text(end + 6, y + height / 2, note, va="center", fontsize=9.5, color=TEXT_SECONDARY)
    bar(0, 0, lx, CURVE)
    bar(-1, 0, lr, SAGITTAL)
    split(-1, 4)
    bar(-2, 0, lp, RESULT)
    split(-2, 6)
    bar(-3, 0, lr, SAGITTAL)
    bar(-3, lr, lh, CURVE)
    ax.text(lr / 2, -3 + height / 2, "r", ha="center", va="center", fontsize=10, color=TEXT_PRIMARY)
    ax.text(
        lr + lh / 2, -3 + height / 2, "h", ha="center", va="center", fontsize=10, color=TEXT_PRIMARY
    )
    for bits in range(0, 385, 64):
        ax.plot([bits] * 2, [-3.25, 0.85], color=GRID, linewidth=0.8, zorder=0)
        ax.text(bits, -3.55, str(bits), ha="center", fontsize=8, color=TEXT_SECONDARY)
    ax.text(0, -3.95, "bits", fontsize=8, color=TEXT_SECONDARY)
    ax.set_xlim(-105, 700)
    ax.set_ylim(-4.1, 1.3)
    ax.set_title(
        "BLS12-377: every size comes from one 64-bit number x (bar lengths in bits)",
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
    primes(args.out / "primes.png")
    print(f"Wrote slicing.png, pippenger.png, ec_add.png, limbs.png and primes.png to {args.out}")


if __name__ == "__main__":
    main()
