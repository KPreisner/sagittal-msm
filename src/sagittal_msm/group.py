# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""The group interface every MSM algorithm is written against.

Swapping curves (or the fast counting group) never touches algorithm code. A group
counts its own operations in its `counter`:

- `add`        full addition of two accumulator points
- `add_mixed`  accumulator + a normalized (affine) point, which is cheaper on real curves
- `double`     point doubling
- `normalize`  conversion to affine, one count per point (batched on real curves)
"""

from collections.abc import Sequence
from typing import Protocol, TypeVar

from sagittal_msm.counters import OpCounter

T = TypeVar("T")


class Group(Protocol[T]):
    name: str
    counter: OpCounter

    @property
    def order(self) -> int:
        """Prime order r of the group. Scalars live in [0, r)."""
        ...

    @property
    def scalar_bits(self) -> int:
        """Bits needed for a scalar: r.bit_length() (253 for BLS12-377)."""
        ...

    def identity(self) -> T: ...

    def generator(self) -> T: ...

    def eq(self, a: T, b: T) -> bool: ...

    def add(self, a: T, b: T) -> T: ...

    def add_mixed(self, a: T, b: T) -> T: ...

    def double(self, a: T) -> T: ...

    def neg(self, a: T) -> T: ...

    def batch_normalize(self, points: Sequence[T]) -> list[T]: ...

    # Uncounted helpers, only for building inputs and checking answers.

    def add_uncounted(self, a: T, b: T) -> T: ...

    def mul_uncounted(self, a: T, k: int) -> T: ...
