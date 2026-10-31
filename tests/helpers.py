# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Shared test helpers."""

import random


def is_probable_prime(n: int, rounds: int = 32) -> bool:
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
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


SMALL_GROUPS = {"mock-bls12-377", "mock-bn254", "goldilocks-jacobian", "goldilocks-xyzz"}


def group_sizes(names: list[str], sizes: list[int], big_max: int = 9) -> list[tuple[str, int]]:
    """(group, n) cases. BLS12-377 and BN254 arithmetic is slow in Python, so those groups only
    get sizes up to big_max; correctness doesn't need more."""
    return [(g, n) for g in names for n in sizes if g in SMALL_GROUPS or n <= big_max]
