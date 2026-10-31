# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""The closed-form model must match measured counts, since benchmarks extrapolate with it."""

import pytest

from sagittal_msm import model
from sagittal_msm.groups import get_group
from sagittal_msm.inputs import random_points, random_scalars
from sagittal_msm.msm import naive, pippenger, sagittal

N = 1 << 12


def assert_close(measured: dict[str, dict[str, int]], predicted: model.Counts) -> None:
    """Every (phase, op) within 2%, or within 2 operations for tiny counts."""
    keys = {(p, op) for p, ops in measured.items() for op in ops}
    keys |= {(p, op) for p, ops in predicted.items() for op, v in ops.items() if v}
    for phase, op in keys:
        got = measured.get(phase, {}).get(op, 0)
        want = predicted.get(phase, {}).get(op, 0)
        assert abs(got - want) <= max(2, 0.02 * want), (phase, op, got, want)


@pytest.fixture(scope="module")
def inputs() -> tuple[list[int], list[int]]:
    group = get_group("mock-bls12-377")
    return random_points(group, N), random_scalars(group, N)


@pytest.mark.parametrize("g", [1, 3, 8])
def test_sagittal_model(inputs: tuple[list[int], list[int]], g: int) -> None:
    group = get_group("mock-bls12-377")
    points, scalars = inputs
    sagittal.msm(group, sagittal.prepare(group, points, g), scalars)
    assert_close(group.counter.as_dict(), model.sagittal(N, group.order, g))


@pytest.mark.parametrize(
    ("c", "signed", "sets"),
    [(4, False, None), (9, False, None), (13, False, None), (5, True, None), (10, True, None),
     (8, True, 1), (12, True, 2), (16, True, 2)],
)  # fmt: skip
def test_pippenger_model(
    inputs: tuple[list[int], list[int]], c: int, signed: bool, sets: int | None
) -> None:
    group = get_group("mock-bls12-377")
    points, scalars = inputs
    pippenger.msm(group, pippenger.prepare(group, points, c, signed, sets), scalars)
    assert_close(group.counter.as_dict(), model.pippenger(N, group.order, c, signed, sets))


def test_naive_model(inputs: tuple[list[int], list[int]]) -> None:
    group = get_group("mock-bls12-377")
    points, scalars = inputs
    naive.msm(group, points, scalars)
    assert_close(group.counter.as_dict(), model.naive(N, group.order))


def test_bit_probability() -> None:
    r = 13  # k in [0, 13): bit 3 is set for 8..12
    assert model.bit_probability(r, 3) == 5 / 13
    assert model.bit_probability(r, 0) == 6 / 13


def test_best_pippenger_grows_with_n() -> None:
    r = get_group("mock-bls12-377").order
    small, large = model.best_pippenger(1 << 10, r), model.best_pippenger(1 << 20, r)
    assert small < large
