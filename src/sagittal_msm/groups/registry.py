# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Groups by name, so benchmarks and tests can swap curves with a flag.

- `mock-<curve>`: the counting group with that curve's subgroup order. Exact group-op counts,
  fast enough for large n.
- `<curve>-jacobian`, `<curve>-xyzz`: real curve arithmetic that also counts field operations.
"""

from collections.abc import Callable
from typing import Any

from sagittal_msm.counters import OpCounter
from sagittal_msm.group import Group
from sagittal_msm.groups.curves import BLS12_377_R, BN254_R, CURVES
from sagittal_msm.groups.mock import MockGroup
from sagittal_msm.groups.weierstrass import CurveParams, JacobianGroup, XYZZGroup

Factory = Callable[[OpCounter | None], Group[Any]]


def _curve_factory(cls: type[JacobianGroup | XYZZGroup], curve: CurveParams) -> Factory:
    return lambda counter: cls(curve, counter)


GROUPS: dict[str, Factory] = {
    "mock-bls12-377": lambda counter: MockGroup(BLS12_377_R, "mock-bls12-377", counter),
    "mock-bn254": lambda counter: MockGroup(BN254_R, "mock-bn254", counter),
}
for _curve in CURVES:
    for _cls in (JacobianGroup, XYZZGroup):
        GROUPS[f"{_curve.name}-{_cls.coords}"] = _curve_factory(_cls, _curve)

MOCK_GROUPS = sorted(name for name in GROUPS if name.startswith("mock-"))
CURVE_GROUPS = sorted(name for name in GROUPS if not name.startswith("mock-"))


def get_group(name: str, counter: OpCounter | None = None) -> Group[Any]:
    try:
        factory = GROUPS[name]
    except KeyError:
        raise ValueError(f"unknown group {name!r}; choose from {sorted(GROUPS)}") from None
    return factory(counter)
