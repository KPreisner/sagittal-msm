# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Baseline MSM: one double-and-add scalar multiplication per point, then sum."""

from collections.abc import Sequence
from typing import TypeVar

from sagittal_msm.group import Group

T = TypeVar("T")


def scalar_mul(group: Group[T], point: T, k: int) -> T:
    """Left-to-right double-and-add. Skips the leading 1 bit, so k costs
    (bit_length - 1) doubles and (popcount - 1) mixed adds."""
    if k == 0:
        return group.identity()
    acc = point
    for i in range(k.bit_length() - 2, -1, -1):
        acc = group.double(acc)
        if (k >> i) & 1:
            acc = group.add_mixed(acc, point)
    return acc


def msm(group: Group[T], points: Sequence[T], scalars: Sequence[int]) -> T:
    if len(points) != len(scalars):
        raise ValueError("points and scalars must have the same length")
    total: T | None = None
    with group.counter.phase("scalar_mul"):
        products = [scalar_mul(group, p, k) for p, k in zip(points, scalars, strict=True) if k]
    with group.counter.phase("sum"):
        for product in products:
            total = product if total is None else group.add(total, product)
    return group.identity() if total is None else total
