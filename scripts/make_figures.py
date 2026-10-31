# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Draw the explanatory (non-data) figures in docs/figures/.

- slicing.png   the scalar bit matrix, cut the Pippenger way and the Sagittal way

Usage: uv run python scripts/make_figures.py
"""

import argparse
import random
from pathlib import Path

# Dataviz reference palette tokens (light mode). Text never wears a series color.
SAGITTAL = "#2a78d6"
PIPPENGER = "#eb6834"
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"

ROWS, BITS = 8, 12
WINDOW, BATCH = 4, 4


def slicing(path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle

    rng = random.Random(7)
    bits = [[rng.randrange(2) for _ in range(BITS)] for _ in range(ROWS)]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150, facecolor=SURFACE)
    panels = [
        ("Pippenger: strips c bits wide, n rows tall", PIPPENGER),
        ("Sagittal: blocks 1 bit wide, g rows tall", SAGITTAL),
    ]
    for ax, (title, _) in zip(axes, panels, strict=True):
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
        ax: object, x: float, y: float, w: float, h: float, color: str, strong: bool
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
        ax.add_patch(box)  # type: ignore[attr-defined]

    left, right = axes
    # Pippenger: every window spans all rows; one is highlighted.
    for w in range(BITS // WINDOW):
        outline(left, w * WINDOW, 0, WINDOW, ROWS, PIPPENGER, w == 1)
    digit = "".join(str(b) for b in bits[2][WINDOW : 2 * WINDOW])
    left.text(
        0,
        ROWS + 0.9,
        f"Each row's {WINDOW}-bit digit picks a bucket: row 3 → bucket {int(digit, 2)} ({digit}).",
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).parent.parent / "docs" / "figures"
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    slicing(args.out / "slicing.png")
    print(f"Wrote slicing.png to {args.out}")


if __name__ == "__main__":
    main()
