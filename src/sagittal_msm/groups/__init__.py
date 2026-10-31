# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Concrete groups: a fast counting group now, real elliptic curves later."""

from sagittal_msm.groups.mock import MockGroup
from sagittal_msm.groups.registry import GROUPS, get_group

__all__ = ["GROUPS", "MockGroup", "get_group"]
