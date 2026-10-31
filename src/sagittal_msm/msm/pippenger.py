# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Pippenger's bucket method, with optional signed digits and precomputed windows.

Write each scalar in base 2^c: W windows of c bits. For one window, every point goes into the
bucket for its digit, so bucket d holds the sum of the points whose digit is d. The window's
contribution is sum(d * bucket[d]), computed with two running sums (about 2 adds per bucket).
Windows are then combined by Horner's rule: c doublings between consecutive windows.

- **Signed digits** use digits in (-2^(c-1), 2^(c-1)], borrowing from the next window, so a
  window needs only 2^(c-1) buckets. A negative digit adds the negated point (negation is free).
- **Precomputed windows** (the approach of the ZPrize 2022 winners, Yrrid and MatterLabs) store
  shifted copies 2^(j*s*c) * P of every point, where s is the number of bucket sets kept. Window
  w of P is then window (w mod s) of copy w // s, so all W windows fold into s bucket sets:
  fewer reductions and fewer doublings, paid for with s*c doublings per extra copy, once.
  Yrrid used c = 23, signed digits, s = 2 (6 shifted copies for 253-bit scalars).

Plain Pippenger is the case with a single copy and s = W bucket sets.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from sagittal_msm.group import Group

T = TypeVar("T")


def num_windows(bits: int, c: int, signed: bool) -> int:
    """Windows needed for `bits`-bit scalars. Signed digits can carry one bit past the top."""
    return -(-(bits + signed) // c)


def num_buckets(c: int, signed: bool) -> int:
    return 1 << (c - 1) if signed else (1 << c) - 1


def digits(k: int, c: int, windows: int, signed: bool) -> list[int]:
    """Base-2^c digits of k, least significant first. Signed digits lie in (-2^(c-1), 2^(c-1)]."""
    mask, half = (1 << c) - 1, 1 << (c - 1)
    out, carry = [], 0
    for w in range(windows):
        d = ((k >> (w * c)) & mask) + carry
        carry = 0
        if signed and d > half:
            d -= 1 << c
            carry = 1
        out.append(d)
    if carry or k >> (windows * c):
        raise ValueError("scalar does not fit in the given windows")
    return out


@dataclass
class PippengerTables(Generic[T]):
    """copies[j][i] = 2^(j * sets * c) * P_i, normalized."""

    c: int
    signed: bool
    sets: int
    windows: int
    copies: list[list[T]]


def prepare(
    group: Group[T], points: Sequence[T], c: int, signed: bool = False, sets: int | None = None
) -> PippengerTables[T]:
    """Precompute shifted copies so the W windows fold into `sets` bucket sets.

    sets=None (the default) keeps one set per window: plain Pippenger, nothing to precompute.
    """
    windows = num_windows(group.scalar_bits, c, signed)
    sets = windows if sets is None else sets
    if not 1 <= sets <= windows:
        raise ValueError(f"sets must be between 1 and {windows}")
    copies = [list(points)]
    with group.counter.phase("prepare"):
        for _ in range(-(-windows // sets) - 1):
            shifted = []
            for p in copies[-1]:
                for _ in range(sets * c):
                    p = group.double(p)
                shifted.append(p)
            copies.append(group.batch_normalize(shifted))
    return PippengerTables(c, signed, sets, windows, copies)


def bucket_sum(group: Group[T], buckets: Sequence[T | None]) -> T | None:
    """sum((i + 1) * buckets[i]) with two running sums, from the top bucket down."""
    running: T | None = None
    total: T | None = None
    for bucket in reversed(buckets):
        if bucket is not None:
            running = bucket if running is None else group.add(running, bucket)
        if running is not None:
            total = running if total is None else group.add(total, running)
    return total


def msm(group: Group[T], tables: PippengerTables[T], scalars: Sequence[int]) -> T:
    if len(scalars) != len(tables.copies[0]):
        raise ValueError("need one scalar per prepared point")
    c, sets = tables.c, tables.sets
    buckets: list[list[T | None]] = [[None] * num_buckets(c, tables.signed) for _ in range(sets)]

    with group.counter.phase("accumulate"):
        for i, k in enumerate(scalars):
            for w, d in enumerate(digits(k, c, tables.windows, tables.signed)):
                if d == 0:
                    continue
                p = tables.copies[w // sets][i]
                if d < 0:
                    p = group.neg(p)
                window_buckets = buckets[w % sets]
                b = window_buckets[abs(d) - 1]
                window_buckets[abs(d) - 1] = p if b is None else group.add_mixed(b, p)

    with group.counter.phase("reduce"):
        set_sums = [bucket_sum(group, b) for b in buckets]

    result: T | None = None
    with group.counter.phase("combine"):
        for s in reversed(set_sums):
            if result is not None:
                for _ in range(c):
                    result = group.double(result)
            if s is not None:
                result = s if result is None else group.add(result, s)
    return group.identity() if result is None else result
