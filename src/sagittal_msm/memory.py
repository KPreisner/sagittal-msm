# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2022-2026 Karl Preisner
"""GPU memory each algorithm needs, in bytes.

Sizes assume values stored in whole 64-bit limbs: an affine point is 2 field elements, an XYZZ
accumulator 4, and a scalar 1 scalar-field element. For BLS12-377 that is 96, 192 and 32 bytes.

Device totals include what stays on the GPU between proofs (input points, precomputed data)
and the scalars of one proof. GPU memory sizes are in GiB (a "16 GB" V100 has 16 GiB).
"""

from sagittal_msm.msm.pippenger import num_buckets, num_windows

# Default per-block shared memory on NVIDIA GPUs. Sagittal's GPU kernel (libsindri's
# MSM_Atomic) copies one batch's table into shared memory; Ampere and later can opt in to more.
SHARED_MEMORY_BYTES = 48 * 1024
GIB = 1 << 30


def element_bytes(p: int) -> int:
    return -(-p.bit_length() // 64) * 8


def affine_bytes(p: int) -> int:
    return 2 * element_bytes(p)


def accumulator_bytes(p: int) -> int:
    """An XYZZ point: X, Y, ZZ, ZZZ."""
    return 4 * element_bytes(p)


def inputs_bytes(n: int, p: int, r: int) -> int:
    """n input points and n scalars."""
    return n * (affine_bytes(p) + element_bytes(r))


def sagittal_table_bytes(n: int, g: int, p: int) -> int:
    """All subset-sum tables: 2^g - 1 affine points per batch of g, the last batch smaller."""
    full, rem = divmod(n, g)
    entries = full * ((1 << g) - 1) + ((1 << rem) - 1)
    return entries * affine_bytes(p)


def sagittal_batch_bytes(g: int, p: int) -> int:
    """One batch's table as the GPU kernel lays it out: 2^g entries, slot 0 the identity."""
    return (1 << g) * affine_bytes(p)


def sagittal_device_bytes(n: int, g: int, p: int, r: int) -> int:
    return inputs_bytes(n, p, r) + sagittal_table_bytes(n, g, p)


def max_batch_size(n: int, budget: int, p: int, r: int, limit: int = 20) -> int:
    """Largest g whose tables, points and scalars fit in `budget` bytes (0 if none do)."""
    fits = [g for g in range(1, limit + 1) if sagittal_device_bytes(n, g, p, r) <= budget]
    return max(fits, default=0)


def max_shared_memory_batch_size(p: int, shared: int = SHARED_MEMORY_BYTES) -> int:
    """Largest g whose single-batch table fits in GPU shared memory."""
    return max(g for g in range(1, 21) if sagittal_batch_bytes(g, p) <= shared)


def pippenger_device_bytes(
    n: int, p: int, r: int, c: int, signed: bool = False, sets: int | None = None
) -> int:
    """Points, scalars, shifted copies (precomputed windows) and bucket accumulators."""
    windows = num_windows(r.bit_length(), c, signed)
    sets = windows if sets is None else sets
    extra_copies = -(-windows // sets) - 1
    copies = extra_copies * n * affine_bytes(p)
    return inputs_bytes(n, p, r) + copies + sets * num_buckets(c, signed) * accumulator_bytes(p)
