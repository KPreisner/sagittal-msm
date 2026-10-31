# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
import pytest

from sagittal_msm.groups import GROUPS, MockGroup, get_group
from sagittal_msm.inputs import expected_msm, random_points, random_scalars
from sagittal_msm.msm import naive, sagittal
from tests.helpers import group_sizes


@pytest.mark.parametrize(("name", "n"), group_sizes(sorted(GROUPS), [1, 7, 33]))
@pytest.mark.parametrize("batch_size", [1, 2, 5, 8])
def test_sagittal_matches_reference(name: str, n: int, batch_size: int) -> None:
    group = get_group(name)
    points = random_points(group, n, seed=n)
    scalars = random_scalars(group, n, seed=n)
    tables = sagittal.prepare(group, points, batch_size)
    assert group.eq(sagittal.msm(group, tables, scalars), expected_msm(group, points, scalars))


@pytest.mark.parametrize("name", sorted(GROUPS))
def test_naive_matches_reference(name: str) -> None:
    group = get_group(name)
    points = random_points(group, 20)
    scalars = random_scalars(group, 20)
    assert group.eq(naive.msm(group, points, scalars), expected_msm(group, points, scalars))


def test_edge_scalars() -> None:
    group = get_group("mock-bls12-377")
    points = random_points(group, 6)
    scalars = [0, 1, 2, group.order - 1, 0, 1 << (group.scalar_bits - 1)]
    want = expected_msm(group, points, scalars)
    assert group.eq(naive.msm(group, points, scalars), want)
    assert group.eq(sagittal.msm(group, sagittal.prepare(group, points, 4), scalars), want)
    zeros = [0] * 6
    assert group.eq(sagittal.msm(group, sagittal.prepare(group, points, 4), zeros), 0)


def test_worked_example() -> None:
    """The README example: tables {A, B, A+B} and {C, D, C+D}, 13A + 6B + 9C + 3D."""
    group = MockGroup(17)
    a, b, c, d = 1, 2, 4, 8
    tables = sagittal.prepare(group, [a, b, c, d], batch_size=2)
    assert tables.tables == [[a, b, a + b], [c, d, c + d]]
    want = (13 * a + 6 * b + 9 * c + 3 * d) % 17
    assert sagittal.msm(group, tables, [13, 6, 9, 3]) == want


def test_table_entries_are_subset_sums() -> None:
    group = MockGroup(1_000_003)
    batch = [3, 50, 700, 9_000, 100_000, 7]
    table = sagittal.build_table(group, batch)
    for mask in range(1, 1 << len(batch)):
        subset = sum(p for t, p in enumerate(batch) if mask >> t & 1)
        assert table[mask - 1] == subset % group.order


@pytest.mark.parametrize("batch_size", [1, 3, 6])
def test_sagittal_exact_counts(batch_size: int) -> None:
    group = get_group("mock-bls12-377")
    n, bits = 50, group.scalar_bits
    points = random_points(group, n)
    scalars = random_scalars(group, n)

    tables = sagittal.prepare(group, points, batch_size)
    sagittal.msm(group, tables, scalars)
    counts = group.counter.as_dict()

    sizes = [len(points[i : i + batch_size]) for i in range(0, n, batch_size)]
    assert counts["prepare"].get("add", 0) == sum((1 << s) - 1 - s for s in sizes)
    assert counts["prepare"]["normalize"] == sum((1 << s) - 1 for s in sizes)

    # One lookup per nonzero (batch, bit) pattern; each bucket's first lookup is a copy.
    lookups, touched = 0, set()
    for j in range(len(sizes)):
        batch = scalars[j * batch_size : (j + 1) * batch_size]
        for i in range(bits):
            if any(k >> i & 1 for k in batch):
                lookups += 1
                touched.add(i)
    assert counts["accumulate"] == {"add_mixed": lookups - len(touched)}

    # Horner from the highest nonempty bucket down: one double per lower bit.
    assert counts["combine"] == {"double": max(touched), "add": len(touched) - 1}


def test_naive_exact_counts() -> None:
    group = get_group("mock-bn254")
    points = random_points(group, 30)
    scalars = random_scalars(group, 30)
    naive.msm(group, points, scalars)
    counts = group.counter.as_dict()
    assert counts["scalar_mul"] == {
        "double": sum(k.bit_length() - 1 for k in scalars),
        "add_mixed": sum(k.bit_count() - 1 for k in scalars),
    }
    assert counts["sum"] == {"add": len(scalars) - 1}
