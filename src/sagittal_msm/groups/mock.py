# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""A counting stand-in for an elliptic curve group: integers mod r under addition.

An elliptic curve subgroup of prime order r is isomorphic to (Z_r, +). MSM algorithms only
use the group operations, so running them here gives exactly the same add/double counts as
on a real curve, without the curve arithmetic. That makes n = 2^20 feasible in Python.
"""

from collections.abc import Sequence

from sagittal_msm.counters import OpCounter


class MockGroup:
    """(Z_r, +) with operation counting. Elements are ints in [0, r); 0 is the identity."""

    def __init__(self, order: int, name: str = "mock", counter: OpCounter | None = None) -> None:
        if order < 2:
            raise ValueError("order must be at least 2")
        self.name = name
        self.counter = counter if counter is not None else OpCounter()
        self._order = order

    @property
    def order(self) -> int:
        return self._order

    @property
    def scalar_bits(self) -> int:
        return self._order.bit_length()

    def identity(self) -> int:
        return 0

    def generator(self) -> int:
        return 1

    def eq(self, a: int, b: int) -> bool:
        return a == b

    def add(self, a: int, b: int) -> int:
        self.counter.record("add")
        return (a + b) % self._order

    def add_mixed(self, a: int, b: int) -> int:
        self.counter.record("add_mixed")
        return (a + b) % self._order

    def double(self, a: int) -> int:
        self.counter.record("double")
        return (2 * a) % self._order

    def neg(self, a: int) -> int:
        self.counter.record("neg")
        return -a % self._order

    def batch_normalize(self, points: Sequence[int]) -> list[int]:
        self.counter.record("normalize", len(points))
        return list(points)

    def add_uncounted(self, a: int, b: int) -> int:
        return (a + b) % self._order

    def mul_uncounted(self, a: int, k: int) -> int:
        return a * k % self._order
