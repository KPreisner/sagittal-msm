# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Find a test curve y^2 = x^3 + b over the Goldilocks field p = 2^64 - 2^32 + 1.

Curves with a = 0 over a field with p = 1 (mod 3) have one of six group orders p + 1 - t, with
t in {+-2u, +-(u + 3v), +-(u - 3v)} where p = u^2 + 3v^2 (found with Cornacchia's algorithm).
For Goldilocks all six orders are composite, so no prime-order a = 0 curve exists. Like
BLS12-377, the curve gets a cofactor: this picks the order with the largest prime factor r,
finds the smallest b with that order (the order that sends a point to the identity), and
uses h * P as the generator of the order-r subgroup, where h = order / r.

The arithmetic here is independent of the library, as a cross-check.

Usage: uv run python scripts/find_goldilocks_curve.py
"""

import math
import random

P = 2**64 - 2**32 + 1


def is_probable_prime(n: int, rounds: int = 40) -> bool:
    if n < 4:
        return n in (2, 3)
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    rng = random.Random(n)
    for _ in range(rounds):
        x = pow(rng.randrange(2, n - 1), d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def sqrt_mod(a: int, p: int) -> int | None:
    """Tonelli-Shanks."""
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


def pollard_rho(n: int) -> int:
    if n % 2 == 0:
        return 2
    rng = random.Random(n)
    while True:
        c, x = rng.randrange(1, n), rng.randrange(2, n)
        y, d = x, 1
        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = math.gcd(abs(x - y), n)
        if d != n:
            return d


def factor(n: int) -> list[int]:
    if n == 1:
        return []
    if is_probable_prime(n):
        return [n]
    d = pollard_rho(n)
    return sorted(factor(d) + factor(n // d))


def cornacchia_3(p: int) -> tuple[int, int]:
    """u, v with u^2 + 3 v^2 = p."""
    r = sqrt_mod(-3, p)
    assert r is not None
    if r < p // 2:
        r = p - r
    a, b = p, r
    while b * b >= p:
        a, b = b, a % b
    rest = p - b * b
    assert rest % 3 == 0
    v = math.isqrt(rest // 3)
    assert b * b + 3 * v * v == p
    return b, v


AffinePoint = tuple[int, int] | None


def add(a: AffinePoint, b: AffinePoint, p: int) -> AffinePoint:
    if a is None:
        return b
    if b is None:
        return a
    (x1, y1), (x2, y2) = a, b
    if x1 == x2:
        if (y1 + y2) % p == 0:
            return None
        lam = 3 * x1 * x1 * pow(2 * y1, -1, p) % p
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (lam * lam - x1 - x2) % p
    return x3, (lam * (x1 - x3) - y1) % p


def mul(a: AffinePoint, k: int, p: int) -> AffinePoint:
    acc: AffinePoint = None
    for i in range(k.bit_length() - 1, -1, -1):
        acc = add(acc, acc, p)
        if (k >> i) & 1:
            acc = add(acc, a, p)
    return acc


def first_point(b: int, p: int) -> tuple[int, int]:
    """Point with the smallest x >= 1, choosing the smaller of the two y values."""
    x = 1
    while True:
        y = sqrt_mod(x**3 + b, p)
        if y is not None and y != 0:
            return x, min(y, p - y)
        x += 1


def main() -> None:
    u, v = cornacchia_3(P)
    traces = {2 * u, -2 * u, u + 3 * v, -(u + 3 * v), u - 3 * v, -(u - 3 * v)}
    print(f"p = {P} = 2^64 - 2^32 + 1 = u^2 + 3v^2 with u = {u}, v = {v}")
    largest = {}
    for n in sorted(P + 1 - t for t in traces):
        factors = factor(n)
        largest[n] = factors[-1]
        print(f"order {n} = {' * '.join(map(str, factors))}")
    order = max(largest, key=lambda n: largest[n])
    r, h = largest[order], order // largest[order]
    print(f"best: order {order}, prime subgroup r = {r} ({r.bit_length()} bits), cofactor {h}")

    for b in range(1, 1000):
        point = first_point(b, P)
        if mul(point, order, P) is not None:
            continue  # this b has a different order
        g = mul(point, h, P)
        if g is None:
            continue
        assert mul(g, r, P) is None
        print(f"\nGOLDILOCKS_B = {b}\nGOLDILOCKS_R = {r}\nGOLDILOCKS_G = {g}")
        return
    raise SystemExit("no curve found")


if __name__ == "__main__":
    main()
