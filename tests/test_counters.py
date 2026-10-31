# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
from sagittal_msm.counters import DEFAULT_PHASE, OpCounter


def test_counts_by_phase() -> None:
    counter = OpCounter()
    counter.record("add")
    with counter.phase("prepare"):
        counter.record("add", 3)
        counter.record("double")
    with counter.phase("accumulate"):
        counter.record("add_mixed", 2)

    assert counter.as_dict() == {
        DEFAULT_PHASE: {"add": 1},
        "prepare": {"add": 3, "double": 1},
        "accumulate": {"add_mixed": 2},
    }
    assert counter.total() == 7
    assert counter.total("add") == 4
    assert counter.total(phase="prepare") == 4
    assert counter.total("add", phase="accumulate") == 0


def test_phase_restores_previous_phase() -> None:
    counter = OpCounter()
    with counter.phase("a"):
        pass
    counter.record("add")
    assert counter.as_dict() == {DEFAULT_PHASE: {"add": 1}}


def test_reset() -> None:
    counter = OpCounter()
    counter.record("add")
    counter.reset()
    assert counter.total() == 0
