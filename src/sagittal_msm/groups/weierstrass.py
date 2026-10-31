# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Short Weierstrass curves y^2 = x^3 + b (a = 0), in Jacobian or XYZZ coordinates.

BN254, BLS12-377 and the Goldilocks test curve all have a = 0. Formulas are from the
Explicit-Formulas Database (https://hyperelliptic.org/EFD/g1p/auto-shortw.html). Each group
counts group operations in `counter` and field operations in `field.counter`, which follows
the group counter's phases.

| coordinates | full add             | mixed add          | double                 |
|-------------|----------------------|--------------------|------------------------|
| Jacobian    | add-2007-bl, 11M+5S  | madd-2007-bl, 7M+4S| dbl-2009-l, 2M+5S      |
| XYZZ        | add-2008-s, 12M+2S   | madd-2008-s, 8M+2S | dbl-2008-s-1, 6M+3S    |

(XYZZ doubling is 6M+4S for general a; with a = 0 the a*ZZ^2 term and its squaring drop out.)

A group operation is counted once when it is called, even when it hits a special case
(identity input, or adding a point to itself, which falls through to doubling). That keeps
group counts identical to the counting group's, while field counts reflect what ran.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sagittal_msm.counters import OpCounter
from sagittal_msm.field import PrimeField

Point = tuple[int, ...]


@dataclass(frozen=True)
class CurveParams:
    """y^2 = x^3 + b over F_p, with a generator of the prime-order subgroup of order r."""

    name: str
    p: int
    b: int
    r: int
    gx: int
    gy: int


class WeierstrassGroup:
    """Shared parts of the Jacobian and XYZZ groups. Subclasses implement the formulas."""

    coords = ""

    def __init__(self, curve: CurveParams, counter: OpCounter | None = None) -> None:
        self.curve = curve
        self.name = f"{curve.name}-{self.coords}"
        self.counter = counter if counter is not None else OpCounter()
        self.field = PrimeField(curve.p)
        self.counter.link(self.field.counter)
        if not self.on_curve(curve.gx, curve.gy):
            raise ValueError(f"{curve.name}: generator is not on the curve")

    @property
    def order(self) -> int:
        return self.curve.r

    @property
    def scalar_bits(self) -> int:
        return self.curve.r.bit_length()

    def on_curve(self, x: int, y: int) -> bool:
        p = self.curve.p
        return (y * y - x * x * x - self.curve.b) % p == 0

    # Public, counted group operations.

    def add(self, a: Point, b: Point) -> Point:
        self.counter.record("add")
        return self._add(a, b)

    def add_mixed(self, a: Point, b: Point) -> Point:
        self.counter.record("add_mixed")
        return self._add_mixed(a, b)

    def double(self, a: Point) -> Point:
        self.counter.record("double")
        return self._double(a)

    def neg(self, a: Point) -> Point:
        self.counter.record("neg")
        return (a[0], self.field.neg(a[1]), *a[2:])

    def batch_normalize(self, points: Sequence[Point]) -> list[Point]:
        self.counter.record("normalize", len(points))
        return self._batch_normalize(points)

    # Uncounted helpers.

    def generator(self) -> Point:
        return self.from_affine(self.curve.gx, self.curve.gy)

    def eq(self, a: Point, b: Point) -> bool:
        return self.to_affine(a) == self.to_affine(b)

    def to_affine(self, a: Point) -> tuple[int, int] | None:
        """(x, y), or None for the identity. Uncounted."""
        if self.is_identity(a):
            return None
        with self.counter.paused():
            normalized = self._batch_normalize([a])[0]
        return normalized[0], normalized[1]

    def add_uncounted(self, a: Point, b: Point) -> Point:
        with self.counter.paused():
            return self._add(a, b)

    def mul_uncounted(self, a: Point, k: int) -> Point:
        """k * a by double-and-add, returned normalized."""
        k %= self.curve.r
        acc = self.identity()
        with self.counter.paused():
            for i in range(k.bit_length() - 1, -1, -1):
                acc = self._double(acc)
                if (k >> i) & 1:
                    acc = self._add(acc, a)
            return self._batch_normalize([acc])[0]

    # Implemented per coordinate system.

    def identity(self) -> Point:
        raise NotImplementedError

    def is_identity(self, a: Point) -> bool:
        raise NotImplementedError

    def from_affine(self, x: int, y: int) -> Point:
        raise NotImplementedError

    def _add(self, a: Point, b: Point) -> Point:
        raise NotImplementedError

    def _add_mixed(self, a: Point, b: Point) -> Point:
        raise NotImplementedError

    def _double(self, a: Point) -> Point:
        raise NotImplementedError

    def _batch_normalize(self, points: Sequence[Point]) -> list[Point]:
        raise NotImplementedError


class JacobianGroup(WeierstrassGroup):
    """(X, Y, Z) represents (X/Z^2, Y/Z^3). Identity has Z = 0; normalized points have Z = 1."""

    coords = "jacobian"

    def identity(self) -> Point:
        return (1, 1, 0)

    def is_identity(self, a: Point) -> bool:
        return a[2] == 0

    def from_affine(self, x: int, y: int) -> Point:
        return (x, y, 1)

    def _add(self, a: Point, b: Point) -> Point:  # add-2007-bl
        if a[2] == 0:
            return b
        if b[2] == 0:
            return a
        f = self.field
        x1, y1, z1 = a
        x2, y2, z2 = b
        z1z1, z2z2 = f.sqr(z1), f.sqr(z2)
        u1, u2 = f.mul(x1, z2z2), f.mul(x2, z1z1)
        s1, s2 = f.mul(f.mul(y1, z2), z2z2), f.mul(f.mul(y2, z1), z1z1)
        h, r = f.sub(u2, u1), f.dbl(f.sub(s2, s1))
        if h == 0:
            return self._double(a) if r == 0 else self.identity()
        i = f.sqr(f.dbl(h))
        j, v = f.mul(h, i), f.mul(u1, i)
        x3 = f.sub(f.sub(f.sqr(r), j), f.dbl(v))
        y3 = f.sub(f.mul(r, f.sub(v, x3)), f.dbl(f.mul(s1, j)))
        z3 = f.mul(f.sub(f.sub(f.sqr(f.add(z1, z2)), z1z1), z2z2), h)
        return (x3, y3, z3)

    def _add_mixed(self, a: Point, b: Point) -> Point:  # madd-2007-bl, b has Z = 1
        if b[2] == 0:
            return a
        if b[2] != 1:
            raise ValueError("add_mixed needs a normalized second point")
        if a[2] == 0:
            return b
        f = self.field
        x1, y1, z1 = a
        x2, y2, _ = b
        z1z1 = f.sqr(z1)
        u2, s2 = f.mul(x2, z1z1), f.mul(f.mul(y2, z1), z1z1)
        h, r = f.sub(u2, x1), f.dbl(f.sub(s2, y1))
        if h == 0:
            return self._double(a) if r == 0 else self.identity()
        hh = f.sqr(h)
        i = f.dbl(f.dbl(hh))
        j, v = f.mul(h, i), f.mul(x1, i)
        x3 = f.sub(f.sub(f.sqr(r), j), f.dbl(v))
        y3 = f.sub(f.mul(r, f.sub(v, x3)), f.dbl(f.mul(y1, j)))
        z3 = f.sub(f.sub(f.sqr(f.add(z1, h)), z1z1), hh)
        return (x3, y3, z3)

    def _double(self, a: Point) -> Point:  # dbl-2009-l
        x, y, z = a
        if z == 0 or y == 0:
            return self.identity()
        f = self.field
        aa, bb = f.sqr(x), f.sqr(y)
        cc = f.sqr(bb)
        d = f.dbl(f.sub(f.sub(f.sqr(f.add(x, bb)), aa), cc))
        e = f.mul3(aa)
        x3 = f.sub(f.sqr(e), f.dbl(d))
        y3 = f.sub(f.mul(e, f.sub(d, x3)), f.mul8(cc))
        z3 = f.dbl(f.mul(y, z))
        return (x3, y3, z3)

    def _batch_normalize(self, points: Sequence[Point]) -> list[Point]:
        f = self.field
        live = [i for i, pt in enumerate(points) if pt[2] != 0]
        inverses = f.batch_inv([points[i][2] for i in live])
        out = list(points)
        for i, z_inv in zip(live, inverses, strict=True):
            x, y, _ = points[i]
            z_inv2 = f.sqr(z_inv)
            out[i] = (f.mul(x, z_inv2), f.mul(y, f.mul(z_inv2, z_inv)), 1)
        return out


class XYZZGroup(WeierstrassGroup):
    """(X, Y, ZZ, ZZZ) represents (X/ZZ, Y/ZZZ), with ZZ^3 = ZZZ^2. Identity has ZZ = 0."""

    coords = "xyzz"

    def identity(self) -> Point:
        return (1, 1, 0, 0)

    def is_identity(self, a: Point) -> bool:
        return a[2] == 0

    def from_affine(self, x: int, y: int) -> Point:
        return (x, y, 1, 1)

    def _add(self, a: Point, b: Point) -> Point:  # add-2008-s
        if a[2] == 0:
            return b
        if b[2] == 0:
            return a
        f = self.field
        x1, y1, zz1, zzz1 = a
        x2, y2, zz2, zzz2 = b
        u1, u2 = f.mul(x1, zz2), f.mul(x2, zz1)
        s1, s2 = f.mul(y1, zzz2), f.mul(y2, zzz1)
        p, r = f.sub(u2, u1), f.sub(s2, s1)
        if p == 0:
            return self._double(a) if r == 0 else self.identity()
        pp = f.sqr(p)
        ppp, q = f.mul(p, pp), f.mul(u1, pp)
        x3 = f.sub(f.sub(f.sqr(r), ppp), f.dbl(q))
        y3 = f.sub(f.mul(r, f.sub(q, x3)), f.mul(s1, ppp))
        return (x3, y3, f.mul(f.mul(zz1, zz2), pp), f.mul(f.mul(zzz1, zzz2), ppp))

    def _add_mixed(self, a: Point, b: Point) -> Point:  # madd-2008-s, b has ZZ = ZZZ = 1
        if b[2] == 0:
            return a
        if b[2] != 1 or b[3] != 1:
            raise ValueError("add_mixed needs a normalized second point")
        if a[2] == 0:
            return b
        f = self.field
        x1, y1, zz1, zzz1 = a
        x2, y2, _, _ = b
        p, r = f.sub(f.mul(x2, zz1), x1), f.sub(f.mul(y2, zzz1), y1)
        if p == 0:
            return self._double(a) if r == 0 else self.identity()
        pp = f.sqr(p)
        ppp, q = f.mul(p, pp), f.mul(x1, pp)
        x3 = f.sub(f.sub(f.sqr(r), ppp), f.dbl(q))
        y3 = f.sub(f.mul(r, f.sub(q, x3)), f.mul(y1, ppp))
        return (x3, y3, f.mul(zz1, pp), f.mul(zzz1, ppp))

    def _double(self, a: Point) -> Point:  # dbl-2008-s-1 with a = 0
        x, y, zz, zzz = a
        if zz == 0 or y == 0:
            return self.identity()
        f = self.field
        u = f.dbl(y)
        v = f.sqr(u)
        w, s = f.mul(u, v), f.mul(x, v)
        m = f.mul3(f.sqr(x))
        x3 = f.sub(f.sqr(m), f.dbl(s))
        y3 = f.sub(f.mul(m, f.sub(s, x3)), f.mul(w, y))
        return (x3, y3, f.mul(v, zz), f.mul(w, zzz))

    def _batch_normalize(self, points: Sequence[Point]) -> list[Point]:
        f = self.field
        live = [i for i, pt in enumerate(points) if pt[2] != 0]
        inverses = f.batch_inv([points[i][2] for i in live] + [points[i][3] for i in live])
        out = list(points)
        for k, i in enumerate(live):
            x, y, _, _ = points[i]
            out[i] = (f.mul(x, inverses[k]), f.mul(y, inverses[len(live) + k]), 1, 1)
        return out
