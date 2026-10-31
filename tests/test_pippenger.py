# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
import pytest

from sagittal_msm.groups import GROUPS, MockGroup, get_group
from sagittal_msm.inputs import expected_msm, random_points, random_scalars
from sagittal_msm.msm import pippenger
from tests.helpers import group_sizes

CONFIGS = [  # (c, signed, sets)
    (1, False, None),
    (4, False, None),
    (7, False, None),
    (4, True, None),
    (8, True, None),
    (5, False, 1),
    (6, True, 1),
    (9, True, 3),
]


@pytest.mark.parametrize(("name", "n"), group_sizes(sorted(GROUPS), [1, 9, 40]))
@pytest.mark.parametrize(("c", "signed", "sets"), CONFIGS)
def test_matches_reference(name: str, c: int, signed: bool, sets: int | None, n: int) -> None:
    group = get_group(name)
    points = random_points(group, n, seed=n)
    scalars = random_scalars(group, n, seed=n)
    tables = pippenger.prepare(group, points, c, signed, sets)
    got = pippenger.msm(group, tables, scalars)
    assert group.eq(got, expected_msm(group, points, scalars))


@pytest.mark.parametrize(("c", "signed", "sets"), CONFIGS)
def test_edge_scalars(c: int, signed: bool, sets: int | None) -> None:
    group = get_group("mock-bls12-377")
    points = random_points(group, 5)
    scalars = [0, 1, group.order - 1, 1 << (group.scalar_bits - 1), (1 << c) - 1]
    tables = pippenger.prepare(group, points, c, signed, sets)
    got = pippenger.msm(group, tables, scalars)
    assert group.eq(got, expected_msm(group, points, scalars))


@pytest.mark.parametrize("signed", [False, True])
@pytest.mark.parametrize("c", [1, 3, 8, 13])
def test_digits_reconstruct_scalar(c: int, signed: bool) -> None:
    group = get_group("mock-bn254")
    windows = pippenger.num_windows(group.scalar_bits, c, signed)
    half = 1 << (c - 1)
    for k in [*random_scalars(group, 50), 0, group.order - 1, (1 << group.scalar_bits) - 1]:
        ds = pippenger.digits(k, c, windows, signed)
        assert sum(d << (w * c) for w, d in enumerate(ds)) == k
        if signed:
            assert all(-half < d <= half for d in ds)
        else:
            assert all(0 <= d < 1 << c for d in ds)


def test_digits_reject_overflow() -> None:
    with pytest.raises(ValueError, match="does not fit"):
        pippenger.digits(1 << 8, 4, 2, signed=False)


def test_bucket_sum() -> None:
    group = MockGroup(1_000_003)
    buckets = [5, None, 7, None, 11]
    assert pippenger.bucket_sum(group, buckets) == 1 * 5 + 3 * 7 + 5 * 11
    # Running sums start at the top bucket: 2 adds per bucket below it, the first is a copy.
    assert group.counter.total("add") == (3 - 1) + 4
    assert pippenger.bucket_sum(group, [None, None]) is None


def test_prepare_counts_and_copies() -> None:
    group = get_group("mock-bls12-377")
    points = random_points(group, 10)
    c, sets = 8, 2
    tables = pippenger.prepare(group, points, c, signed=True, sets=sets)
    windows = pippenger.num_windows(group.scalar_bits, c, True)
    copies = -(-windows // sets)
    assert len(tables.copies) == copies
    for j, copy in enumerate(tables.copies):
        assert copy == [group.mul_uncounted(p, 1 << (j * sets * c)) for p in points]
    assert group.counter.as_dict() == {
        "prepare": {"double": 10 * (copies - 1) * sets * c, "normalize": 10 * (copies - 1)}
    }


def test_plain_pippenger_prepares_nothing() -> None:
    group = get_group("mock-bls12-377")
    tables = pippenger.prepare(group, random_points(group, 10), 6)
    assert len(tables.copies) == 1
    assert group.counter.total() == 0


@pytest.mark.parametrize("sets", [0, 100])
def test_prepare_rejects_bad_sets(sets: int) -> None:
    group = get_group("mock-bls12-377")
    with pytest.raises(ValueError, match="sets must be"):
        pippenger.prepare(group, random_points(group, 2), 8, sets=sets)


def test_exact_accumulate_and_combine_counts() -> None:
    group = get_group("mock-bls12-377")
    n, c, signed = 200, 6, True
    points = random_points(group, n)
    scalars = random_scalars(group, n)
    tables = pippenger.prepare(group, points, c, signed)
    pippenger.msm(group, tables, scalars)
    counts = group.counter.as_dict()

    windows = tables.windows
    all_digits = [pippenger.digits(k, c, windows, signed) for k in scalars]
    nonzero = sum(d != 0 for ds in all_digits for d in ds)
    touched = sum(len({abs(ds[w]) for ds in all_digits if ds[w]}) for w in range(windows))
    negative = sum(d < 0 for ds in all_digits for d in ds)
    assert counts["accumulate"] == {"add_mixed": nonzero - touched, "neg": negative}
    assert counts["combine"] == {"double": (windows - 1) * c, "add": windows - 1}
