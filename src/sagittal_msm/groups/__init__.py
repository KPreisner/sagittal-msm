# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Concrete groups: a fast counting group, and real elliptic curves that count field operations."""

from sagittal_msm.groups.mock import MockGroup
from sagittal_msm.groups.registry import CURVE_GROUPS, GROUPS, MOCK_GROUPS, get_group

__all__ = ["CURVE_GROUPS", "GROUPS", "MOCK_GROUPS", "MockGroup", "get_group"]
