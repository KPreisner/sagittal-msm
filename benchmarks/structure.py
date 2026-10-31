# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Structural costs that operation counts don't show: bucket state, load balance, work left
after accumulation, precompute, memory, and total cost amortized over K proofs.

All values are from the closed-form model (tests check it against measured counts). Writes:

- structure.csv   one row per algorithm
- structure.md    the structure table and the amortization table
- structure.png   per-proof field multiplications per point, split by phase

Usage: uv run python benchmarks/structure.py [--log-n 20] [--curve bls12-377]
"""

import argparse
import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sagittal_msm import memory, model
from sagittal_msm.costs import multiplications, per_proof_multiplications, total_multiplications
from sagittal_msm.groups.curves import CURVES
from sagittal_msm.groups.weierstrass import CurveParams
from sagittal_msm.msm.pippenger import num_buckets, num_windows

COORDS = "xyzz"
PHASES = ["accumulate", "reduce", "combine"]

# Chart colors: categorical slots 1-3 and text/surface tokens of the dataviz reference palette
# (validated as a set, light mode). Text never wears a series color.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
PROOFS = [1, 10, 100, 1000]
YRRID_C, YRRID_SETS = 23, 2


@dataclass
class Config:
    label: str
    counts: Callable[[int, int], model.Counts]
    loads: Callable[[int, int], tuple[float, int]]
    buckets: Callable[[int], int]  # scalar bits -> accumulators held
    device: Callable[[int, CurveParams], int]  # bytes


def pippenger_config(label: str, c: int | None, signed: bool, sets: int | None) -> Config:
    def window(n: int, r: int) -> int:
        return c if c is not None else model.best_pippenger(n, r, signed)

    return Config(
        label,
        lambda n, r: model.pippenger(n, r, window(n, r), signed, sets),
        lambda n, r: model.pippenger_loads(n, r, window(n, r), signed, sets),
        lambda bits: 0,  # filled in per n below; depends on the chosen c
        lambda n, cv: memory.pippenger_device_bytes(n, cv.p, cv.r, window(n, cv.r), signed, sets),
    )


def sagittal_config(g: int, note: str) -> Config:
    return Config(
        f"Sagittal (g = {g}, {note})",
        lambda n, r: model.sagittal(n, r, g),
        lambda n, r: model.sagittal_loads(n, r, g),
        lambda bits: bits,
        lambda n, cv: memory.sagittal_device_bytes(n, g, cv.p, cv.r),
    )


@dataclass
class Row:
    label: str
    buckets: int
    mean_load: float
    max_load: int
    after_accumulation: float  # reduce + combine EC ops per proof
    per_proof_mults: float  # per point
    prepare_mults: float  # per point
    device_gib: float
    phase_mults: dict[str, float]  # per point, per-proof phases


def compute(curve: CurveParams, log_n: int) -> list[Row]:
    n, r, bits = 1 << log_n, curve.r, curve.r.bit_length()
    best_c = model.best_pippenger(n, r, signed=True)
    configs = [
        sagittal_config(7, "logged GPU run"),
        sagittal_config(9, "shared-memory limit"),
        pippenger_config(f"Pippenger, signed digits (c = {best_c})", best_c, True, None),
        pippenger_config(
            f"Precomputed windows (Yrrid: c = {YRRID_C}, {YRRID_SETS} sets)",
            YRRID_C,
            True,
            YRRID_SETS,
        ),
    ]
    bucket_counts = [
        bits,
        bits,
        num_windows(bits, best_c, True) * num_buckets(best_c, True),
        YRRID_SETS * num_buckets(YRRID_C, True),
    ]
    rows = []
    for config, buckets in zip(configs, bucket_counts, strict=True):
        counts = config.counts(n, r)
        mean, top = config.loads(n, r)
        after = sum(
            ops.get(op, 0)
            for phase in ("reduce", "combine")
            for ops in [counts.get(phase, {})]
            for op in model.EC_OPS
        )
        rows.append(
            Row(
                label=config.label,
                buckets=buckets,
                mean_load=mean,
                max_load=top,
                after_accumulation=after,
                per_proof_mults=per_proof_multiplications(counts, COORDS) / n,
                prepare_mults=total_multiplications({"prepare": counts.get("prepare", {})}, COORDS)
                / n,
                device_gib=config.device(n, curve) / memory.GIB,
                phase_mults={
                    phase: multiplications(counts.get(phase, {}), COORDS) / n for phase in PHASES
                },
            )
        )
    return rows


def write_csv(path: Path, rows: list[Row]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "algorithm",
                "buckets",
                "mean_load",
                "max_load",
                "after_accumulation_ops",
                "per_proof_mults_per_point",
                "prepare_mults_per_point",
                "device_gib",
            ]
        )
        for x in rows:
            writer.writerow(
                [
                    x.label,
                    x.buckets,
                    round(x.mean_load, 2),
                    x.max_load,
                    round(x.after_accumulation),
                    round(x.per_proof_mults, 1),
                    round(x.prepare_mults, 1),
                    round(x.device_gib, 2),
                ]
            )


def amortized(row: Row, proofs: int) -> float:
    return row.per_proof_mults + row.prepare_mults / proofs


def break_even(a: Row, b: Row) -> float | None:
    """Proofs per key above which b's total cost per proof drops below a's (None: never)."""
    saving = a.per_proof_mults - b.per_proof_mults
    extra = b.prepare_mults - a.prepare_mults
    if saving <= 0:
        return None
    return max(0.0, extra / saving)


def write_markdown(path: Path, rows: list[Row], curve: CurveParams, log_n: int) -> None:
    lines = [
        f"Structure of each algorithm at n = 2^{log_n} on {curve.name}, from the closed-form "
        "model. Generated by `benchmarks/structure.py`.",
        "",
        "- **Buckets** are the accumulators held during one MSM. On a GPU each is a unit of "
        "parallel work that needs its own storage and synchronization.",
        "- **Points per bucket**: mean, and the expected maximum (median). Sagittal's loads are "
        "fixed by n and g before seeing any scalars: each bucket gets one table lookup per "
        "batch. Pippenger's depend on the scalars (Poisson spread), and with textbook signed "
        "digits the top window can send a large share of all points to one bucket. Real GPU "
        "codes mitigate this: Yrrid sorts buckets by size and negates scalars with the top bit "
        "set, which this model does not include.",
        "- **After accumulation** is EC operations that start only once every bucket is final: "
        "Pippenger's bucket reduction and window combine, Sagittal's combine.",
        "- **Field mults** are per point, XYZZ (mul + sqr). **Device memory** is points, scalars "
        f"and precomputed data ({memory.affine_bytes(curve.p)}-byte points).",
        "",
        "| Algorithm | Buckets | Points per bucket (mean / max) | After accumulation | "
        "Per-proof field mults | Precompute field mults | Device memory |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in rows:
        lines.append(
            f"| {x.label} | {x.buckets:,} | {x.mean_load:,.1f} / {x.max_load:,} "
            f"| {x.after_accumulation:,.0f} | {x.per_proof_mults:,.0f} | {x.prepare_mults:,.0f} "
            f"| {x.device_gib:,.2f} GiB |"
        )
    lines += [
        "",
        "### Cost per proof when one precompute serves K proofs",
        "",
        "Field multiplications per point per proof: per-proof work + precompute / K. A proving "
        "key is fixed for a circuit, so its precompute is paid once and reused by every proof.",
        "",
        "| Algorithm | " + " | ".join(f"K = {k:,}" for k in PROOFS) + " |",
        "|---|" + "---|" * len(PROOFS),
    ]
    for x in rows:
        lines.append(
            f"| {x.label} | " + " | ".join(f"{amortized(x, k):,.0f}" for k in PROOFS) + " |"
        )
    lines += ["", "Break-even: proofs per key above which the second algorithm costs less.", ""]
    for a in rows:
        for b in rows:
            if a is b:
                continue
            k = break_even(a, b)
            if k is not None and k > 0:
                lines.append(f"- {b.label} beats {a.label} above {k:,.0f} proofs per key")
    path.write_text("\n".join(lines) + "\n")


def plot(path: Path, rows: list[Row], curve: CurveParams, log_n: int) -> None:
    import matplotlib

    matplotlib.use("Agg")  # render to files, no window
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "text.color": TEXT_PRIMARY,
            "axes.labelcolor": TEXT_SECONDARY,
            "xtick.color": TEXT_SECONDARY,
            "ytick.color": TEXT_SECONDARY,
            "axes.edgecolor": GRID,
        }
    )
    fig, ax = plt.subplots(figsize=(9, 4), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    labels = [x.label for x in rows][::-1]  # first row at the top
    ordered = rows[::-1]
    left = [0.0] * len(rows)
    # Combining is a few hundred operations per MSM at most: too small to see, so it is drawn
    # together with the bucket reduction as the work left after accumulation.
    segments: dict[str, Callable[[Row], float]] = {
        "Accumulate": lambda x: x.phase_mults["accumulate"],
        "Reduce and combine (after accumulation)": lambda x: (
            x.phase_mults["reduce"] + x.phase_mults["combine"]
        ),
    }
    for (name, width), color in zip(segments.items(), SERIES, strict=False):
        widths = [width(x) for x in ordered]
        # A 2 px surface-colored edge separates adjacent segments.
        ax.barh(labels, widths, left=left, color=color, edgecolor=SURFACE, linewidth=2,
                height=0.6, label=name)  # fmt: skip
        left = [a + b for a, b in zip(left, widths, strict=True)]
    for y, (x, total) in enumerate(zip(ordered, left, strict=True)):
        ax.text(total + 6, y, f"{x.per_proof_mults:,.0f}", va="center", fontsize=9,
                color=TEXT_PRIMARY)  # fmt: skip
    ax.set_xlim(0, max(left) * 1.12)
    ax.xaxis.set_major_formatter(lambda value, _: f"{value:,.0f}")
    ax.set_title(f"Where per-proof work goes at $2^{{{log_n}}}$ points ({curve.name})",
                 fontsize=11, loc="left", pad=28)  # fmt: skip
    ax.set_xlabel("Field multiplications per point (XYZZ, mul + sqr)")
    ax.grid(True, axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncols=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log-n", type=int, default=20)
    parser.add_argument("--curve", choices=[c.name for c in CURVES], default="bls12-377")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()

    curve = next(c for c in CURVES if c.name == args.curve)
    rows = compute(curve, args.log_n)
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "structure.csv", rows)
    write_markdown(args.out / "structure.md", rows, curve, args.log_n)
    plot(args.out / "structure.png", rows, curve, args.log_n)
    print(f"Wrote structure.csv, structure.md, and structure.png to {args.out}")


if __name__ == "__main__":
    main()
