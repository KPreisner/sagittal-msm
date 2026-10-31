# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Compare per-proof operation counts of Sagittal and Pippenger variants across MSM sizes.

Counts come from the closed-form model (`sagittal_msm.model`) for every size up to 2^24, and
are measured on the counting group for sizes up to --max-measured-log-n, where each measured
result is checked against the reference answer and against the model. Writes:

- compare.csv   every algorithm and size: model and measured per-proof ops, precompute, storage
- compare.md    Markdown table of the same
- compare.png   per-proof EC operations per point vs. n (lines: model, dots: measured)

Usage: uv run python benchmarks/compare.py [--max-measured-log-n 14] [--group mock-bls12-377]
"""

import argparse
import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sagittal_msm import model
from sagittal_msm.group import Group
from sagittal_msm.groups import GROUPS, get_group
from sagittal_msm.inputs import expected_msm, random_points, random_scalars
from sagittal_msm.msm import pippenger, sagittal

# Chart colors: categorical slots 1-3 and text/surface tokens of the dataviz reference palette
# (validated as a set, light mode). Text never wears a series color.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"

SAGITTAL_G = 7  # the batch size of the logged GPU benchmark (atomic:7, 64 ms at 2^20)
YRRID_C, YRRID_SETS = 23, 2  # Yrrid's ZPrize 2022 configuration

Y_MIN, Y_MAX = 8, 300
LABEL_DY = {"Sagittal": 0, "Pippenger": 6, "Yrrid config": -7}  # keep end labels apart


@dataclass
class Algorithm:
    label: str
    short: str  # direct label on the chart
    params: Callable[[int, int], dict[str, Any]]  # (n, r) -> parameters for this size
    predict: Callable[..., model.Counts]
    run: Callable[..., dict[str, dict[str, int]]]
    storage: Callable[[dict[str, Any], int], float]  # points stored per input point


def run_sagittal(group: Group[Any], points: list[Any], scalars: list[int], g: int) -> Any:
    return sagittal.msm(group, sagittal.prepare(group, points, g), scalars)


def run_pippenger(
    group: Group[Any], points: list[Any], scalars: list[int], c: int, signed: bool,
    sets: int | None,
) -> Any:  # fmt: skip
    return pippenger.msm(group, pippenger.prepare(group, points, c, signed, sets), scalars)


def windows_copies(p: dict[str, Any], bits: int) -> float:
    windows = pippenger.num_windows(bits, p["c"], p["signed"])
    return float(-(-windows // (p["sets"] or windows)))


ALGORITHMS = [
    Algorithm(
        f"Sagittal (g = {SAGITTAL_G})",
        "Sagittal",
        lambda n, r: {"g": SAGITTAL_G},
        lambda n, r, g: model.sagittal(n, r, g),
        run_sagittal,
        lambda p, bits: ((1 << p["g"]) - 1) / p["g"],
    ),
    Algorithm(
        "Pippenger, signed digits (best c)",
        "Pippenger",
        lambda n, r: {"c": model.best_pippenger(n, r, True), "signed": True, "sets": None},
        lambda n, r, c, signed, sets: model.pippenger(n, r, c, signed, sets),
        run_pippenger,
        windows_copies,
    ),
    Algorithm(
        f"Precomputed windows (Yrrid: c = {YRRID_C}, {YRRID_SETS} sets)",
        "Yrrid config",
        lambda n, r: {"c": YRRID_C, "signed": True, "sets": YRRID_SETS},
        lambda n, r, c, signed, sets: model.pippenger(n, r, c, signed, sets),
        run_pippenger,
        windows_copies,
    ),
    Algorithm(
        "Pippenger, unsigned (best c)",
        "",  # table only: within 6% of signed, would crowd the chart
        lambda n, r: {"c": model.best_pippenger(n, r, False), "signed": False, "sets": None},
        lambda n, r, c, signed, sets: model.pippenger(n, r, c, signed, sets),
        run_pippenger,
        windows_copies,
    ),
]


@dataclass
class Result:
    algorithm: str
    log_n: int
    params: str
    model_per_point: float
    measured_per_point: float | None
    prepare_per_point: float
    storage: float


def measure(group_name: str, log_ns: range, max_measured: int) -> list[Result]:
    group = get_group(group_name)
    r, bits = group.order, group.scalar_bits
    results = []
    for log_n in log_ns:
        n = 1 << log_n
        if log_n <= max_measured:
            points = random_points(group, n)
            scalars = random_scalars(group, n)
            want = expected_msm(group, points, scalars)
        for alg in ALGORITHMS:
            p = alg.params(n, r)
            predicted = alg.predict(n, r, **p)
            measured = None
            if log_n <= max_measured:
                group.counter.reset()
                assert group.eq(alg.run(group, points, scalars, **p), want)
                counts = group.counter.as_dict()
                measured = model.per_proof({k: dict(v) for k, v in counts.items()}) / n
                expected = model.per_proof(predicted) / n
                assert abs(measured - expected) <= 0.02 * expected, (alg.label, log_n)
            results.append(
                Result(
                    algorithm=alg.label,
                    log_n=log_n,
                    params=", ".join(f"{k}={v}" for k, v in p.items() if v is not None),
                    model_per_point=model.per_proof(predicted) / n,
                    measured_per_point=measured,
                    prepare_per_point=sum(predicted.get("prepare", {}).values()) / n,
                    storage=alg.storage(p, bits),
                )
            )
            shown = f"{measured:8.2f} measured" if measured is not None else " " * 17
            print(f"2^{log_n:<2} {alg.label:<46} {results[-1].model_per_point:9.2f} model {shown}",
                  flush=True)  # fmt: skip
    return results


def write_csv(path: Path, results: list[Result]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "algorithm",
                "log_n",
                "params",
                "model_ops_per_point",
                "measured_ops_per_point",
                "prepare_ops_per_point",
                "storage_x_n",
            ]
        )
        for x in results:
            measured = "" if x.measured_per_point is None else round(x.measured_per_point, 3)
            writer.writerow(
                [
                    x.algorithm,
                    x.log_n,
                    x.params,
                    round(x.model_per_point, 3),
                    measured,
                    round(x.prepare_per_point, 3),
                    round(x.storage, 2),
                ]
            )


def write_markdown(path: Path, results: list[Result], group_name: str, bits: int) -> None:
    sizes = sorted({x.log_n for x in results})
    lines = [
        f"Per-proof EC operations per point on `{group_name}` ({bits}-bit scalars). "
        "Generated by `benchmarks/compare.py`.",
        "",
        "- **Per proof** excludes one-time precompute, which is reused across proofs that share "
        "a proving key.",
        "- Values are from the closed-form model; sizes marked * were also measured, and "
        "measured counts match the model within 2%.",
        "- **Storage** is points kept per input point (Sagittal tables, Yrrid's shifted copies).",
        "- Sagittal is flat in n: it does b(1 - 2^-g)/g lookups per point whatever n is, and "
        "has no bucket reduction to amortize. Pippenger's best window c grows with n, so its "
        "cost per point falls. Sagittal's equivalent, g, grows only with table memory "
        "((2^g - 1)/g points per input point).",
        "",
        "| Algorithm | Storage | " + " | ".join(f"2^{s}" for s in sizes) + " |",
        "|---|---|" + "---|" * len(sizes),
    ]
    for alg in ALGORITHMS:
        rows = [x for x in results if x.algorithm == alg.label]
        cells = [
            f"{x.model_per_point:,.1f}" + ("*" if x.measured_per_point is not None else "")
            for x in rows
        ]
        lines.append(f"| {alg.label} | {rows[-1].storage:,.1f}x | " + " | ".join(cells) + " |")
    lines += ["", "Window sizes chosen for each n (best per-proof count):", ""]
    for alg in ALGORITHMS:
        if "best c" in alg.label:
            rows = [x for x in results if x.algorithm == alg.label]
            lines.append(f"- {alg.label}: " + ", ".join(f"2^{x.log_n}: {x.params.split(',')[0]}"
                                                       for x in rows))  # fmt: skip
    path.write_text("\n".join(lines) + "\n")


def plot(path: Path, results: list[Result], bits: int) -> None:
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
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    charted = [alg for alg in ALGORITHMS if alg.short]
    for alg, color in zip(charted, SERIES, strict=True):
        rows = [x for x in results if x.algorithm == alg.label]
        x = [row.log_n for row in rows]
        ax.plot(x, [row.model_per_point for row in rows], color=color, linewidth=1.5,
                label=alg.label)  # fmt: skip
        measured = [row for row in rows if row.measured_per_point is not None]
        ax.plot([row.log_n for row in measured], [row.measured_per_point for row in measured],
                linestyle="none", marker="o", markersize=5, color=color)  # fmt: skip
        ax.annotate(
            alg.short,
            (x[-1], rows[-1].model_per_point),
            xytext=(8, LABEL_DY[alg.short]),
            textcoords="offset points",
            va="center",
            fontsize=9,
            color=TEXT_SECONDARY,
        )
    measured_max = max(x.log_n for x in results if x.measured_per_point is not None)
    ax.axvspan(min(x.log_n for x in results) - 0.5, measured_max + 0.5, color=GRID, alpha=0.35,
               linewidth=0)  # fmt: skip
    ax.text(0.01, 0.98, "Measured", transform=ax.transAxes, ha="left", va="top", fontsize=8,
            color=TEXT_SECONDARY)  # fmt: skip
    ax.set_yscale("log")
    # Small-n counts for the Yrrid config run into the thousands; they are in the table.
    ax.set_ylim(Y_MIN, Y_MAX)
    sizes = sorted({x.log_n for x in results})
    ax.set_xticks(sizes, [f"$2^{{{s}}}$" for s in sizes])
    ax.set_xlim(sizes[0] - 0.5, sizes[-1] + 2.6)
    ax.set_yticks([10, 20, 30, 50, 100, 200])
    ax.yaxis.set_minor_formatter(lambda value, _: "")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:,.0f}")
    ax.set_title(
        f"Per-proof EC operations per point ({bits}-bit scalars)\n"
        "lines: closed-form model, dots: measured",
        fontsize=11,
    )
    ax.set_xlabel("MSM size, n (points)")
    ax.set_ylabel("EC operations per point (log scale)")
    ax.grid(True, which="major", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--min-log-n", type=int, default=10)
    parser.add_argument("--max-log-n", type=int, default=24)
    parser.add_argument("--max-measured-log-n", type=int, default=14)
    parser.add_argument("--group", choices=sorted(GROUPS), default="mock-bls12-377")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()

    log_ns = range(args.min_log_n, args.max_log_n + 1, 2)
    results = measure(args.group, log_ns, args.max_measured_log_n)
    bits = get_group(args.group).scalar_bits

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "compare.csv", results)
    write_markdown(args.out / "compare.md", results, args.group, bits)
    plot(args.out / "compare.png", results, bits)
    print(f"Wrote compare.csv, compare.md, and compare.png to {args.out}")


if __name__ == "__main__":
    main()
