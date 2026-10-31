# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Prime field arithmetic that counts its own operations.

Elements are plain ints in [0, p). Counted operations:

- `mul`  multiplication
- `sqr`  squaring (cheaper than mul in hardware, so counted separately)
- `add`  addition, subtraction, negation, or multiplication by 2 (one modular add each)
- `inv`  inversion

Multiplication by a small constant is done with adds and counted as such: x3 = 2 adds,
x8 = 3 adds. This is the convention of the Explicit-Formulas Database, where those count
as additions rather than multiplications.
"""

from sagittal_msm.counters import OpCounter


class PrimeField:
    def __init__(self, p: int, counter: OpCounter | None = None) -> None:
        self.p = p
        self.counter = counter if counter is not None else OpCounter()

    def mul(self, a: int, b: int) -> int:
        self.counter.record("mul")
        return a * b % self.p

    def sqr(self, a: int) -> int:
        self.counter.record("sqr")
        return a * a % self.p

    def add(self, a: int, b: int) -> int:
        self.counter.record("add")
        return (a + b) % self.p

    def sub(self, a: int, b: int) -> int:
        self.counter.record("add")
        return (a - b) % self.p

    def neg(self, a: int) -> int:
        self.counter.record("add")
        return -a % self.p

    def dbl(self, a: int) -> int:
        """2a, one modular addition."""
        self.counter.record("add")
        return 2 * a % self.p

    def mul3(self, a: int) -> int:
        """3a = 2a + a, two modular additions."""
        self.counter.record("add", 2)
        return 3 * a % self.p

    def mul8(self, a: int) -> int:
        """8a by three doublings."""
        self.counter.record("add", 3)
        return 8 * a % self.p

    def inv(self, a: int) -> int:
        if a % self.p == 0:
            raise ZeroDivisionError("0 has no inverse")
        self.counter.record("inv")
        return pow(a, -1, self.p)

    def batch_inv(self, values: list[int]) -> list[int]:
        """Inverses of nonzero values with one inversion (Montgomery's trick): 3(N - 1) muls."""
        if not values:
            return []
        prefix = [values[0]]
        for v in values[1:]:
            prefix.append(self.mul(prefix[-1], v))
        inv = self.inv(prefix[-1])
        out = [0] * len(values)
        for i in range(len(values) - 1, 0, -1):
            out[i] = self.mul(inv, prefix[i - 1])
            inv = self.mul(inv, values[i])
        out[0] = inv
        return out

    def sqrt(self, a: int) -> int | None:
        """A square root of a, or None (Tonelli-Shanks). Uncounted; for building inputs."""
        p = self.p
        a %= p
        if a == 0:
            return 0
        if pow(a, (p - 1) // 2, p) != 1:
            return None
        q, s = p - 1, 0
        while q % 2 == 0:
            q, s = q // 2, s + 1
        z = 2
        while pow(z, (p - 1) // 2, p) != p - 1:
            z += 1
        m, c, t, r = s, pow(z, q, p), pow(a, q, p), pow(a, (q + 1) // 2, p)
        while t != 1:
            i, t2 = 0, t
            while t2 != 1:
                t2, i = t2 * t2 % p, i + 1
            b = pow(c, 1 << (m - i - 1), p)
            m, c, t, r = i, b * b % p, t * b * b % p, r * b % p
        return r
