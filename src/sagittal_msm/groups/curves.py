# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""Curve constants. Every curve is y^2 = x^3 + b, with a generator of its order-r subgroup.

Tests check each generator is on its curve, r is prime, and r * G is the identity.
"""

from sagittal_msm.groups.weierstrass import CurveParams

# BLS12-377 G1 prime subgroup order r (253 bits). ZPrize 2022 MSM curve.
BLS12_377_R = 0x12AB655E9A2CA55660B44D1E5C37B00159AA76FED00000010A11800000000001

# BN254 (alt_bn128) G1 prime subgroup order r (254 bits). Ethereum's pairing curve.
BN254_R = 21888242871839275222246405745257275088548364400416034343698204186575808495617

BLS12_377 = CurveParams(
    name="bls12-377",
    p=0x01AE3A4617C510EAC63B05C06CA1493B1A22D9F300F5138F1EF3622FBA094800170B5D44300000008508C00000000001,
    b=1,
    r=BLS12_377_R,
    gx=0x008848DEFE740A67C8FC6225BF87FF5485951E2CAA9D41BB188282C8BD37CB5CD5481512FFCD394EEAB9B16EB21BE9EF,
    gy=0x01914A69C5102EFF1F674F5D30AFEEC4BD7FB348CA3E52D96D182AD44FB82305C2FE3D3634A9591AFD82DE55559C8EA6,
)  # fmt: skip

BN254 = CurveParams(
    name="bn254",
    p=21888242871839275222246405745257275088696311157297823662689037894645226208583,
    b=3,
    r=BN254_R,
    gx=1,
    gy=2,
)

# A small test curve over the 64-bit Goldilocks field p = 2^64 - 2^32 + 1, so field elements
# fit in a uint64. No a = 0 curve over this field has prime order; this one has order
# 2^64 + 3 = 467443687 * r, and G generates the 36-bit subgroup of order r.
# Found by scripts/find_goldilocks_curve.py.
GOLDILOCKS = CurveParams(
    name="goldilocks",
    p=2**64 - 2**32 + 1,
    b=11,
    r=39463029637,
    gx=9908814736768235447,
    gy=4429091643524615636,
)

CURVES = [BLS12_377, BN254, GOLDILOCKS]
