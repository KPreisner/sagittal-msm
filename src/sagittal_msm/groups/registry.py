# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Groups by name, so benchmarks and tests can swap curves with a flag."""

from collections.abc import Callable
from typing import Any

from sagittal_msm.counters import OpCounter
from sagittal_msm.group import Group
from sagittal_msm.groups.curves import BLS12_377_R, BN254_R
from sagittal_msm.groups.mock import MockGroup

GROUPS: dict[str, Callable[[OpCounter | None], Group[Any]]] = {
    "mock-bls12-377": lambda counter: MockGroup(BLS12_377_R, "mock-bls12-377", counter),
    "mock-bn254": lambda counter: MockGroup(BN254_R, "mock-bn254", counter),
}


def get_group(name: str, counter: OpCounter | None = None) -> Group[Any]:
    try:
        factory = GROUPS[name]
    except KeyError:
        raise ValueError(f"unknown group {name!r}; choose from {sorted(GROUPS)}") from None
    return factory(counter)
