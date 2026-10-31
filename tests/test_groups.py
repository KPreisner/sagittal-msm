# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
import pytest

from sagittal_msm.groups import GROUPS, MockGroup, get_group
from sagittal_msm.groups.curves import BLS12_377_R, BN254_R
from tests.helpers import is_probable_prime


@pytest.mark.parametrize(("order", "bits"), [(BLS12_377_R, 253), (BN254_R, 254)])
def test_curve_orders_are_prime(order: int, bits: int) -> None:
    assert order.bit_length() == bits
    assert is_probable_prime(order)


def test_mock_group_arithmetic_and_counts() -> None:
    group = MockGroup(17)
    assert group.add(16, 3) == 2
    assert group.add_mixed(5, 5) == 10
    assert group.double(9) == 1
    assert group.neg(5) == 12
    assert group.batch_normalize([1, 2, 3]) == [1, 2, 3]
    assert group.add_uncounted(16, 1) == 0
    assert group.mul_uncounted(3, 6) == 1
    assert group.counter.as_dict() == {
        "other": {"add": 1, "add_mixed": 1, "double": 1, "neg": 1, "normalize": 3}
    }


@pytest.mark.parametrize("name", sorted(GROUPS))
def test_registry_builds_every_group(name: str) -> None:
    group = get_group(name)
    assert group.name == name
    assert group.scalar_bits == group.order.bit_length()


def test_registry_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown group"):
        get_group("not-a-curve")
