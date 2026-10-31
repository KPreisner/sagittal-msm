# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Seeded MSM inputs, so every run and every algorithm sees the same data."""

import random
from collections.abc import Sequence
from typing import TypeVar

from sagittal_msm.group import Group

T = TypeVar("T")


def random_scalars(group: Group[T], n: int, seed: int = 1) -> list[int]:
    """n uniform scalars in [0, r)."""
    rng = random.Random(f"scalars-{seed}")
    return [rng.randrange(group.order) for _ in range(n)]


def random_points(group: Group[T], n: int, seed: int = 1) -> list[T]:
    """n random nonzero multiples of the generator."""
    rng = random.Random(f"points-{seed}")
    g = group.generator()
    return [group.mul_uncounted(g, rng.randrange(1, group.order)) for _ in range(n)]


def expected_msm(group: Group[T], points: Sequence[T], scalars: Sequence[int]) -> T:
    """Reference answer sum(k_i * P_i), computed without counting."""
    total = group.identity()
    for p, k in zip(points, scalars, strict=True):
        total = group.add_uncounted(total, group.mul_uncounted(p, k))
    return total
