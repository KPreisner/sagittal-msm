# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Field operations per group operation, for curves with a = 0.

Multiplication and squaring counts are the Explicit-Formulas Database figures for the formulas
in `groups/weierstrass.py`; additions are what that code executes (subtractions, negations
and small-constant multiples count as additions). Tests check these against measured counts.

Normalization is per point in a large batch: batch inversion costs 3 multiplications per value
plus one inversion for the whole batch, which is ignored here. Jacobian inverts Z (then 3M+1S
per point); XYZZ inverts ZZ and ZZZ (then 2M per point).

The usual cost summary is field multiplications, mul + sqr: on GPUs and in hardware a squaring
costs about as much as a multiplication, and additions are much cheaper than either.
"""

from collections.abc import Mapping

FieldOps = dict[str, int]

COSTS: dict[str, dict[str, FieldOps]] = {
    "jacobian": {
        "add": {"mul": 11, "sqr": 5, "add": 13},
        "add_mixed": {"mul": 7, "sqr": 4, "add": 14},
        "double": {"mul": 2, "sqr": 5, "add": 14},
        "neg": {"add": 1},
        "normalize": {"mul": 6, "sqr": 1},
    },
    "xyzz": {
        "add": {"mul": 12, "sqr": 2, "add": 7},
        "add_mixed": {"mul": 8, "sqr": 2, "add": 7},
        "double": {"mul": 6, "sqr": 3, "add": 7},
        "neg": {"add": 1},
        "normalize": {"mul": 8},
    },
}


def field_ops(group_ops: Mapping[str, float], coords: str) -> dict[str, float]:
    """Field operations for a {group op: count} mapping."""
    out: dict[str, float] = {}
    for op, count in group_ops.items():
        for field_op, per in COSTS[coords].get(op, {}).items():
            out[field_op] = out.get(field_op, 0) + per * count
    return out


def multiplications(group_ops: Mapping[str, float], coords: str) -> float:
    """Field multiplications (mul + sqr) for a {group op: count} mapping."""
    ops = field_ops(group_ops, coords)
    return ops.get("mul", 0) + ops.get("sqr", 0)


def per_proof_multiplications(counts: Mapping[str, Mapping[str, float]], coords: str) -> float:
    """Field multiplications (mul + sqr) for {phase: {group op: count}}, excluding the one-time
    `prepare` phase."""
    return sum(multiplications(ops, coords) for phase, ops in counts.items() if phase != "prepare")


def total_multiplications(counts: Mapping[str, Mapping[str, float]], coords: str) -> float:
    """Field multiplications (mul + sqr) for {phase: {group op: count}}, all phases."""
    return sum(multiplications(ops, coords) for ops in counts.values())
