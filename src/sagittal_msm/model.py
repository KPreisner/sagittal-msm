# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Closed-form expected operation counts, for sizes too large to run in Python (2^20+).

Each function returns the same shape as `OpCounter.as_dict()`: {phase: {op: expected count}},
for n uniform random scalars in [0, r). Tests check these against measured counts.

Bucket occupancy uses the Poisson approximation: a bucket hit at rate lam per MSM is empty
with probability exp(-lam).
"""

import math
from collections.abc import Sequence

from sagittal_msm.msm.pippenger import num_buckets, num_windows

Counts = dict[str, dict[str, float]]


EC_OPS = ("add", "add_mixed", "double")


def per_proof(counts: Counts) -> float:
    """EC additions and doublings, excluding the one-time `prepare` phase. Negations (one field
    subtraction each) and normalization are left out."""
    return sum(
        ops.get(op, 0) for phase, ops in counts.items() if phase != "prepare" for op in EC_OPS
    )


def bit_probability(r: int, i: int) -> float:
    """P(bit i is set) for k uniform in [0, r)."""
    full, rest = r >> (i + 1), r & ((1 << (i + 1)) - 1)
    return ((full << i) + max(0, rest - (1 << i))) / r


def naive(n: int, r: int) -> Counts:
    bits = r.bit_length()
    p = [bit_probability(r, i) for i in range(bits)]
    expected_bitlen = sum(length * (min(r, 1 << length) - (1 << (length - 1))) / r
                          for length in range(1, bits + 1))  # fmt: skip
    return {
        "scalar_mul": {"double": n * (expected_bitlen - 1), "add_mixed": n * (sum(p) - 1)},
        "sum": {"add": n - 1},
    }


def sagittal(n: int, r: int, g: int) -> Counts:
    bits = r.bit_length()
    full, rem = divmod(n, g)
    p = [bit_probability(r, i) for i in range(bits)]
    lookups = sum(full * (1 - (1 - pi) ** g) + (1 - (1 - pi) ** rem if rem else 0) for pi in p)
    touched = [1 - (1 - pi) ** n for pi in p]
    # Horner starts at the highest nonempty bucket h and doubles once per lower bit: E[h].
    top = sum(1 - math.prod((1 - pi) ** n for pi in p[j:]) for j in range(1, bits))
    return {
        "prepare": {
            "add": full * ((1 << g) - 1 - g) + ((1 << rem) - 1 - rem),
            "normalize": full * ((1 << g) - 1) + ((1 << rem) - 1),
        },
        "accumulate": {"add_mixed": lookups - sum(touched)},
        "combine": {"double": top, "add": sum(touched) - 1},
    }


def _sum_one_minus_exp(above: float, lam: float, length: int) -> float:
    """sum_{t=1..length} (1 - exp(-(above + t * lam)))."""
    if lam == 0:
        return length * (1 - math.exp(-above))
    ratio = math.exp(-lam)
    return length - math.exp(-above) * ratio * (1 - ratio**length) / (1 - ratio)


def bucket_stats(segments: Sequence[tuple[int, float]]) -> tuple[float, float]:
    """Expected (touched buckets, index of the highest touched bucket) for buckets listed
    bottom-up as segments of (count, hit rate per MSM)."""
    touched = sum(count * (1 - math.exp(-lam)) for count, lam in segments)
    above, top_sum = 0.0, 0.0
    for count, lam in reversed(segments):
        top_sum += _sum_one_minus_exp(above, lam, count)
        above += count * lam
    # top_sum counted P(h >= j) for every j >= 0; E[h] sums only j >= 1.
    return touched, top_sum - (1 - math.exp(-above))


Segments = list[tuple[int, float]]  # (bucket count, hit rate per MSM), bottom-up


def _window_segments(n: int, r: int, c: int, signed: bool, w: int, windows: int) -> Segments:
    """Expected hits per MSM on the buckets (bottom-up) from window w of n scalars."""
    buckets = num_buckets(c, signed)
    if w < windows - 1:
        if signed:
            # Magnitudes 1 .. 2^(c-1)-1 come from two residues each, 2^(c-1) from one.
            return [(buckets - 1, 2.0 * n / (1 << c)), (1, 1.0 * n / (1 << c))]
        return [(buckets, 1.0 * n / (1 << c))]
    # Top window: the digit (plus any carry) is roughly uniform over [0, m).
    m = max(2, -(-r // (1 << (w * c))))
    used = min(m - 1, buckets)
    return [(used, 1.0 * n / m), (buckets - used, 0.0)]


def _add_segments(a: Segments, b: Segments) -> Segments:
    """Pointwise sum of two piecewise-constant rate lists covering the same buckets."""
    out: Segments = []
    i = j = 0
    left_a, left_b = (a[0][0] if a else 0), (b[0][0] if b else 0)
    while i < len(a) and j < len(b):
        step = min(left_a, left_b)
        if step:
            lam = a[i][1] + b[j][1]
            if out and out[-1][1] == lam:
                out[-1] = (out[-1][0] + step, lam)
            else:
                out.append((step, lam))
        left_a -= step
        left_b -= step
        if left_a == 0:
            i += 1
            left_a = a[i][0] if i < len(a) else 0
        if left_b == 0:
            j += 1
            left_b = b[j][0] if j < len(b) else 0
    return out


def pippenger(n: int, r: int, c: int, signed: bool = False, sets: int | None = None) -> Counts:
    bits = r.bit_length()
    windows = num_windows(bits, c, signed)
    sets = windows if sets is None else sets
    copies = -(-windows // sets)
    buckets = num_buckets(c, signed)

    # Signed digits are negative for residues above 2^(c-1); the top window never is.
    negations = (windows - 1) * n * ((1 << (c - 1)) - 1) / (1 << c) if signed else 0.0
    accumulate = reduce_adds = 0.0
    for s in range(sets):
        segments: Segments = [(buckets, 0.0)]
        for w in range(s, windows, sets):
            segments = _add_segments(segments, _window_segments(n, r, c, signed, w, windows))
        hits = sum(count * lam for count, lam in segments)  # nonzero digits landing here
        touched, top = bucket_stats(segments)
        accumulate += hits - touched
        reduce_adds += (touched - 1) + top

    return {
        "prepare": {
            "double": n * (copies - 1) * sets * c,
            "normalize": n * (copies - 1),
        },
        "accumulate": {"add_mixed": accumulate, "neg": negations},
        "reduce": {"add": reduce_adds},
        "combine": {"double": (sets - 1) * c, "add": sets - 1},
    }


def best_pippenger(
    n: int, r: int, signed: bool = False, sets: int | None = None, c_range: range = range(2, 25)
) -> int:
    """Window size c with the fewest expected per-proof operations."""
    return min(c_range, key=lambda c: per_proof(pippenger(n, r, c, signed, sets)))
