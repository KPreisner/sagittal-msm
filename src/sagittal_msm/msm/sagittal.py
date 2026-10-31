# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Sagittal MSM.

Write the n scalars as rows of b bits. Pippenger cuts that bit matrix into strips c bits
wide and n rows tall. Sagittal cuts it into blocks 1 bit wide and g rows tall:

- **prepare** (once per set of points, e.g. a proving key): split the points into batches
  of g and build every subset sum of each batch. Entry m - 1 of a batch's table is the sum of
  the points whose bit is set in m. Each entry costs one addition.
- **accumulate** (per proof): for each batch and each bit position i, the g scalar bits at
  position i form a pattern m, and bucket[i] += table[m - 1]. There is one bucket per bit.
- **combine**: result = sum(2^i * bucket[i]), by Horner's rule: b - 1 doublings in total.

With g = 1 there is no precompute: each point is its own table, and the algorithm is plain
bit-sliced double-and-add with shared doublings.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from sagittal_msm.group import Group

T = TypeVar("T")


@dataclass
class SagittalTables(Generic[T]):
    """Precomputed subset sums. tables[j][m - 1] is the sum of batch j's points in mask m."""

    batch_size: int
    n_points: int
    tables: list[list[T]]


def build_table(group: Group[T], batch: Sequence[T]) -> list[T]:
    """All 2^len(batch) - 1 nonempty subset sums, one addition per non-singleton entry.

    Slot c holds the subset with bitmask c + 1. d = c & (c + 1) clears the trailing 1-bits
    of c, splitting mask c + 1 into its low run (slot c - d) and the rest (slot d - 1).
    Both are smaller, so they are already built. When d == 0 the mask is a single point.
    """
    table: list[T] = []
    next_point = 0
    for c in range((1 << len(batch)) - 1):
        d = c & (c + 1)
        if d:
            table.append(group.add(table[c - d], table[d - 1]))
        else:
            table.append(batch[next_point])
            next_point += 1
    return table


def prepare(group: Group[T], points: Sequence[T], batch_size: int) -> SagittalTables[T]:
    """Build the subset-sum tables. The last batch may be smaller than batch_size."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    with group.counter.phase("prepare"):
        tables = [
            group.batch_normalize(build_table(group, points[i : i + batch_size]))
            for i in range(0, len(points), batch_size)
        ]
    return SagittalTables(batch_size, len(points), tables)


def msm(group: Group[T], tables: SagittalTables[T], scalars: Sequence[int]) -> T:
    if len(scalars) != tables.n_points:
        raise ValueError("need one scalar per prepared point")
    bits = group.scalar_bits
    g = tables.batch_size
    # None marks an untouched bucket: its first table entry is copied, not added.
    buckets: list[T | None] = [None] * bits

    with group.counter.phase("accumulate"):
        for j, table in enumerate(tables.tables):
            batch_scalars = scalars[j * g : (j + 1) * g]
            for i in range(bits):
                pattern = 0
                for t, k in enumerate(batch_scalars):
                    pattern |= ((k >> i) & 1) << t
                if pattern:
                    entry = table[pattern - 1]
                    bucket = buckets[i]
                    buckets[i] = entry if bucket is None else group.add_mixed(bucket, entry)

    result: T | None = None
    with group.counter.phase("combine"):
        for bucket in reversed(buckets):
            if result is not None:
                result = group.double(result)
            if bucket is not None:
                result = bucket if result is None else group.add(result, bucket)
    return group.identity() if result is None else result
