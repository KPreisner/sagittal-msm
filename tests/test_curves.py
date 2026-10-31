# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
import random

import pytest

from sagittal_msm.costs import COSTS
from sagittal_msm.counters import OpCounter
from sagittal_msm.field import PrimeField
from sagittal_msm.groups import CURVE_GROUPS, get_group
from sagittal_msm.groups.curves import CURVES, GOLDILOCKS
from sagittal_msm.groups.weierstrass import CurveParams, JacobianGroup, Point, WeierstrassGroup
from tests.helpers import is_probable_prime

Affine = tuple[int, int] | None


def affine_add(curve: CurveParams, a: Affine, b: Affine) -> Affine:
    """Textbook affine addition, independent of the projective formulas under test."""
    p = curve.p
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


def projective_pair(group: WeierstrassGroup, seed: int) -> tuple[Point, Point, Point, Point]:
    """Two random normalized points and non-normalized (Z != 1) versions of two others."""
    rng = random.Random(seed)
    g = group.generator()
    a, b = (group.mul_uncounted(g, rng.randrange(1, group.order)) for _ in range(2))
    with group.counter.paused():
        pa, pb = group._double(a), group._double(group._double(b))
    return a, b, pa, pb


@pytest.mark.parametrize("curve", CURVES, ids=lambda c: c.name)
def test_curve_parameters(curve: CurveParams) -> None:
    group = JacobianGroup(curve)
    assert group.on_curve(curve.gx, curve.gy)
    assert is_probable_prime(curve.r)
    assert is_probable_prime(curve.p)
    # (r - 1) * G + G is the identity, and G itself is not: G has order exactly r.
    g = group.generator()
    minus_g = group.mul_uncounted(g, curve.r - 1)
    assert group.to_affine(minus_g) == (curve.gx, -curve.gy % curve.p)
    assert group.is_identity(group.add_uncounted(minus_g, g))


def test_goldilocks_order() -> None:
    assert GOLDILOCKS.p == 2**64 - 2**32 + 1 < 2**64
    assert 467443687 * GOLDILOCKS.r == 2**64 + 3


@pytest.mark.parametrize("name", CURVE_GROUPS)
def test_formulas_match_affine_reference(name: str) -> None:
    group = get_group(name)
    assert isinstance(group, WeierstrassGroup)
    curve = group.curve
    for seed in range(5):
        a, b, pa, pb = projective_pair(group, seed)
        aa, ab, apa, apb = (group.to_affine(x) for x in (a, b, pa, pb))
        assert group.to_affine(group.add(pa, pb)) == affine_add(curve, apa, apb)
        assert group.to_affine(group.add_mixed(pa, b)) == affine_add(curve, apa, ab)
        assert group.to_affine(group.double(pa)) == affine_add(curve, apa, apa)
        assert group.to_affine(group.add(a, b)) == affine_add(curve, aa, ab)
        for x in (a, b, pa, pb):
            ax = group.to_affine(x)
            assert ax is not None and group.on_curve(*ax)


@pytest.mark.parametrize("name", CURVE_GROUPS)
def test_special_cases(name: str) -> None:
    group = get_group(name)
    assert isinstance(group, WeierstrassGroup)
    a, _, pa, _ = projective_pair(group, 7)
    o = group.identity()
    assert group.eq(group.add(pa, pa), group.double(pa))
    assert group.eq(group.add_mixed(pa, a), group.add(pa, a))
    assert group.is_identity(group.add(pa, group.neg(pa)))
    assert group.is_identity(group.add_mixed(a, group.neg(a)))
    assert group.eq(group.add(o, pa), pa)
    assert group.eq(group.add(pa, o), pa)
    assert group.eq(group.add_mixed(o, a), a)
    assert group.is_identity(group.double(o))
    assert group.to_affine(o) is None
    assert group.batch_normalize([o, a])[0] == o
    with pytest.raises(ValueError, match="normalized"):
        group.add_mixed(a, pa)


@pytest.mark.parametrize("name", CURVE_GROUPS)
@pytest.mark.parametrize("op", ["add", "add_mixed", "double"])
def test_field_costs_match_table(name: str, op: str) -> None:
    group = get_group(name)
    assert isinstance(group, WeierstrassGroup)
    _, b, pa, pb = projective_pair(group, 3)
    group.counter.reset()
    {"add": lambda: group.add(pa, pb), "add_mixed": lambda: group.add_mixed(pa, b),
     "double": lambda: group.double(pa)}[op]()  # fmt: skip
    assert group.counter.as_dict() == {"other": {op: 1}}
    assert group.field.counter.as_dict() == {"other": COSTS[group.coords][op]}


@pytest.mark.parametrize("name", CURVE_GROUPS)
def test_batch_normalize_uses_one_inversion(name: str) -> None:
    group = get_group(name)
    assert isinstance(group, WeierstrassGroup)
    _, _, pa, pb = projective_pair(group, 5)
    group.counter.reset()
    out = group.batch_normalize([pa, pb, pa, pb])
    assert group.field.counter.total("inv") == 1
    assert group.counter.as_dict() == {"other": {"normalize": 4}}
    for x, y in zip(out, [pa, pb, pa, pb], strict=True):
        assert x[2] == 1 and group.eq(x, y)


def test_field_counter_follows_group_phases() -> None:
    counter = OpCounter()
    group = get_group("bn254-xyzz", counter)
    assert isinstance(group, WeierstrassGroup)
    _, b, pa, _ = projective_pair(group, 1)
    counter.reset()
    with counter.phase("accumulate"):
        group.add_mixed(pa, b)
    with counter.paused():
        group.double(pa)
    assert counter.as_dict() == {"accumulate": {"add_mixed": 1}}
    assert group.field.counter.as_dict() == {"accumulate": COSTS["xyzz"]["add_mixed"]}
    counter.reset()
    assert group.field.counter.total() == 0


def test_field_operations() -> None:
    f = PrimeField(101)
    assert f.mul(7, 30) == 210 % 101
    assert f.sqr(12) == 144 % 101
    assert f.add(100, 5) == 4
    assert f.sub(3, 5) == 99
    assert f.neg(1) == 100
    assert f.dbl(60) == 19
    assert f.mul3(40) == 19
    assert f.mul8(13) == 3
    assert f.inv(3) * 3 % 101 == 1
    assert f.counter.as_dict() == {"other": {"mul": 1, "sqr": 1, "add": 9, "inv": 1}}
    values = [3, 50, 7, 99]
    assert [v * i % 101 for v, i in zip(values, f.batch_inv(values), strict=True)] == [1] * 4
    with pytest.raises(ZeroDivisionError):
        f.inv(0)
    for a in range(1, 101):
        root = f.sqrt(a)
        assert (root is None) == (pow(a, 50, 101) != 1)
        assert root is None or root * root % 101 == a


@pytest.mark.parametrize("coords", ["jacobian", "xyzz"])
@pytest.mark.parametrize("algorithm", ["sagittal", "pippenger"])
def test_measured_field_ops_equal_group_ops_times_costs(coords: str, algorithm: str) -> None:
    """Per phase, field ops are exactly group ops x COSTS, so the cost table can weight the
    model's group-op counts at sizes too large to run on a real curve."""
    from sagittal_msm.costs import field_ops
    from sagittal_msm.inputs import random_points, random_scalars
    from sagittal_msm.msm import pippenger, sagittal

    group = get_group(f"goldilocks-{coords}")
    assert isinstance(group, WeierstrassGroup)
    points, scalars = random_points(group, 300), random_scalars(group, 300)
    group.counter.reset()
    if algorithm == "sagittal":
        sagittal.msm(group, sagittal.prepare(group, points, 4), scalars)
    else:
        pippenger.msm(group, pippenger.prepare(group, points, 6, True, 2), scalars)
    group_counts = group.counter.as_dict()
    field_counts = group.field.counter.as_dict()
    for phase in ("accumulate", "reduce", "combine"):
        if phase in group_counts:
            assert field_counts[phase] == field_ops(group_counts[phase], coords), phase
