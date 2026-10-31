# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Closed-form expected operation counts, for sizes too large to run in Python (2^20+).

Each function returns the same shape as `OpCounter.as_dict()`: {phase: {op: expected count}},
for n uniform random scalars in [0, r). Tests check these against measured counts.

Bucket occupancy uses the Poisson approximation: a bucket hit at rate lam per MSM is empty
with probability exp(-lam).
"""

import itertools
import math
from collections.abc import Callable, Sequence

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


def _range(buckets: int, start: int, stop: int, lam: float) -> Segments:
    """Rate lam on bucket indices [start, stop), 0 elsewhere."""
    start, stop = max(0, start), min(buckets, stop)
    if stop <= start or lam == 0:
        return [(buckets, 0.0)]
    parts = [(start, 0.0), (stop - start, lam), (buckets - stop, 0.0)]
    return [(count, rate) for count, rate in parts if count]


def _window_count(x: int, c: int, w: int, j: int) -> int:
    """How many integers in [0, x) have window w (bits wc .. wc + c - 1) equal to j."""
    shift = 1 << (w * c)
    cycles, rest = divmod(x, shift << c)
    return cycles * shift + min(max(rest - j * shift, 0), shift)


def _window_runs(lo: int, hi: int, c: int, w: int) -> list[tuple[int, int, float]]:
    """Exact distribution of window w's value for x uniform in [lo, hi), as runs
    (first value, end value, probability of each value in the run)."""
    shift, full = 1 << (w * c), 1 << c
    cuts = {0, full}
    for x in (lo, hi):
        j = (x % (shift << c)) // shift
        cuts |= {j, j + 1}
    edges = sorted(e for e in cuts if 0 <= e <= full)
    size = hi - lo
    runs = []
    for a, b in itertools.pairwise(edges):
        prob = (_window_count(hi, c, w, a) - _window_count(lo, c, w, a)) / size
        if prob > 0:
            runs.append((a, b, prob))
    return runs


def _windows(n: int, r: int, c: int, signed: bool) -> list[tuple[Segments, float]]:
    """For each window, bottom-up: expected hits per bucket, and expected negative digits.

    Unsigned digits are the base-2^c digits u of k, uniform in [0, r). Signed digits in
    [-(2^(c-1) - 1), 2^(c-1)], the range `pippenger.digits` produces, are exactly u - o where
    u are the base-2^c digits of k + H, o = 2^(c-1) - 1 and H = o * sum(2^(w c)). Since k + H is
    uniform in [H, H + r), every window's distribution is exact, carries included.
    """
    buckets, half = num_buckets(c, signed), 1 << (c - 1)
    windows = num_windows(r.bit_length(), c, signed)
    offset = half - 1 if signed else 0
    h = offset * sum(1 << (w * c) for w in range(windows))
    out: list[tuple[Segments, float]] = []
    for w in range(windows):
        segments: Segments = [(buckets, 0.0)]
        negatives = 0.0
        for lo, hi, prob in _window_runs(h, h + r, c, w):
            # digit u - offset > 0 lands in bucket u - offset - 1
            pos_lo = max(lo, offset + 1)
            if pos_lo < hi:
                part = _range(buckets, pos_lo - offset - 1, hi - offset - 1, n * prob)
                segments = _add_segments(segments, part)
            # digit u - offset < 0 has magnitude offset - u and lands in bucket offset - u - 1
            neg_hi = min(hi, offset)
            if lo < neg_hi:
                negatives += n * (neg_hi - lo) * prob
                part = _range(buckets, offset - neg_hi, offset - lo, n * prob)
                segments = _add_segments(segments, part)
        out.append((segments, negatives))
    return out


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


def _bucket_sets(
    n: int, r: int, c: int, signed: bool, sets: int | None
) -> tuple[list[Segments], float, int, int]:
    """Hit rates of each bucket set, expected negations, number of sets and of copies."""
    windows = _windows(n, r, c, signed)
    sets = len(windows) if sets is None else sets
    rates: list[Segments] = []
    for s in range(sets):
        segments: Segments = [(num_buckets(c, signed), 0.0)]
        for window_segments, _ in windows[s::sets]:
            segments = _add_segments(segments, window_segments)
        rates.append(segments)
    negations = sum(neg for _, neg in windows)
    return rates, negations, sets, -(-len(windows) // sets)


def pippenger(n: int, r: int, c: int, signed: bool = False, sets: int | None = None) -> Counts:
    rates, negations, sets, copies = _bucket_sets(n, r, c, signed, sets)
    accumulate = reduce_adds = 0.0
    for segments in rates:
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


# Bucket loads: how many points land in one bucket. On a GPU, buckets are the units of parallel
# work, so the largest bucket bounds how long accumulation takes. Each function returns
# (mean load over buckets, median of the maximum load), estimated without running anything.


def _median_of_max(log_cdf: Callable[[int], float], high: int) -> int:
    """Smallest k with P(max load <= k) >= 1/2, given log P(max <= k) for k in [0, high]."""
    low = 0
    while low < high:
        mid = (low + high) // 2
        if log_cdf(mid) >= math.log(0.5):
            high = mid
        else:
            low = mid + 1
    return low


def _normal_log_cdf(z: float) -> float:
    phi = 0.5 * math.erfc(-z / math.sqrt(2))
    return math.log(phi) if phi > 0 else -math.inf


def _poisson_log_cdf(k: int, lam: float) -> float:
    """log P(X <= k) for X ~ Poisson(lam). Exact for small lam, normal approximation above 100."""
    if lam == 0 or k > lam + 12 * math.sqrt(lam) + 30:
        return 0.0
    if lam > 100:
        return _normal_log_cdf((k + 0.5 - lam) / math.sqrt(lam))
    terms = [i * math.log(lam) - lam - math.lgamma(i + 1) for i in range(k + 1)]
    top = max(terms)
    return min(0.0, top + math.log(sum(math.exp(t - top) for t in terms)))


def sagittal_loads(n: int, r: int, g: int) -> tuple[float, int]:
    """Bucket i (one per scalar bit) gets one lookup per batch whose bit-i column is nonzero."""
    bits, batches = r.bit_length(), n / g
    hit = [1 - (1 - bit_probability(r, i)) ** g for i in range(bits)]
    means = [batches * q for q in hit]
    sds = [math.sqrt(batches * q * (1 - q)) or 1e-9 for q in hit]

    def log_cdf(k: int) -> float:  # normal approximation to each binomial
        total = 0.0
        for mu, sd in zip(means, sds, strict=True):
            total += _normal_log_cdf((k + 0.5 - mu) / sd)
        return total

    return sum(means) / bits, _median_of_max(log_cdf, math.ceil(batches))


def pippenger_loads(
    n: int, r: int, c: int, signed: bool = False, sets: int | None = None
) -> tuple[float, int]:
    """Bucket hits are Poisson with the rates used by `pippenger()`."""
    rates, _, _, _ = _bucket_sets(n, r, c, signed, sets)
    segments = [segment for set_rates in rates for segment in set_rates]
    buckets = sum(count for count, _ in segments)
    mean = sum(count * lam for count, lam in segments) / buckets
    top = max(lam for _, lam in segments)

    def log_cdf(k: int) -> float:
        return sum(count * _poisson_log_cdf(k, lam) for count, lam in segments if lam)

    return mean, _median_of_max(log_cdf, math.ceil(top * 4 + 50))
