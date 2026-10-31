# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
from collections import Counter

import pytest

from sagittal_msm import memory, model
from sagittal_msm.groups import get_group
from sagittal_msm.groups.curves import BLS12_377, BN254
from sagittal_msm.inputs import random_scalars
from sagittal_msm.msm import pippenger


def test_sizes() -> None:
    assert memory.affine_bytes(BLS12_377.p) == 96
    assert memory.accumulator_bytes(BLS12_377.p) == 192
    assert memory.affine_bytes(BN254.p) == 64
    assert memory.inputs_bytes(10, BLS12_377.p, BLS12_377.r) == 10 * (96 + 32)


def test_sagittal_table_bytes() -> None:
    # 10 points in batches of 4: two full tables of 15 entries and one of 2^2 - 1 = 3.
    assert memory.sagittal_table_bytes(10, 4, BLS12_377.p) == (15 + 15 + 3) * 96
    assert memory.sagittal_batch_bytes(8, BLS12_377.p) == 256 * 96


@pytest.mark.parametrize(("log_n", "g"), [(22, 8), (24, 5)])
def test_reproduces_logged_v100_batch_sizes(log_n: int, g: int) -> None:
    """The logged runs on a 16 GiB V100 used the largest g that fits: 8 at 2^22, 5 at 2^24."""
    n = 1 << log_n
    budget = 16 * memory.GIB
    assert memory.max_batch_size(n, budget, BLS12_377.p, BLS12_377.r) == g
    assert memory.sagittal_device_bytes(n, g + 1, BLS12_377.p, BLS12_377.r) > budget


def test_shared_memory_limit() -> None:
    """One 2^g-entry table must fit in 48 KB: g = 9 for 96-byte points (the 4x A40 run used 9)."""
    assert memory.max_shared_memory_batch_size(BLS12_377.p) == 9
    assert memory.max_shared_memory_batch_size(BN254.p) == 9


def test_nothing_fits() -> None:
    assert memory.max_batch_size(1 << 20, 1, BLS12_377.p, BLS12_377.r) == 0


def test_pippenger_device_bytes() -> None:
    n, p, r = 1 << 10, BLS12_377.p, BLS12_377.r
    plain = memory.pippenger_device_bytes(n, p, r, 8, signed=True)
    windows = pippenger.num_windows(253, 8, True)
    assert plain == memory.inputs_bytes(n, p, r) + windows * 128 * 192
    folded = memory.pippenger_device_bytes(n, p, r, 8, signed=True, sets=2)
    copies = -(-windows // 2)
    assert folded == memory.inputs_bytes(n, p, r) + (copies - 1) * n * 96 + 2 * 128 * 192


N = 1 << 14


@pytest.mark.parametrize("g", [1, 4, 7])
def test_sagittal_loads_match_extracted(g: int) -> None:
    group = get_group("mock-bls12-377")
    scalars = random_scalars(group, N, seed=g)
    loads: Counter[int] = Counter()
    for j in range(0, N, g):
        batch = scalars[j : j + g]
        for i in range(group.scalar_bits):
            if any(k >> i & 1 for k in batch):
                loads[i] += 1
    mean, top = model.sagittal_loads(N, group.order, g)
    assert abs(sum(loads.values()) / group.scalar_bits - mean) <= 0.01 * mean
    assert abs(max(loads.values()) - top) <= 0.02 * top


@pytest.mark.parametrize(
    ("c", "signed", "sets"), [(8, False, None), (10, True, None), (9, True, 2)]
)
def test_pippenger_loads_match_extracted(c: int, signed: bool, sets: int | None) -> None:
    group = get_group("mock-bls12-377")
    scalars = random_scalars(group, N, seed=c)
    windows = pippenger.num_windows(group.scalar_bits, c, signed)
    sets_ = windows if sets is None else sets
    loads: Counter[tuple[int, int]] = Counter()
    for k in scalars:
        for w, d in enumerate(pippenger.digits(k, c, windows, signed)):
            if d:
                loads[(w % sets_, abs(d) - 1)] += 1
    mean, top = model.pippenger_loads(N, group.order, c, signed, sets)
    buckets = sets_ * pippenger.num_buckets(c, signed)
    assert abs(sum(loads.values()) / buckets - mean) <= 0.02 * mean
    assert abs(max(loads.values()) - top) <= 0.15 * top
