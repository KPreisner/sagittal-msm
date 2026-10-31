# Sagittal MSM

A bit-sliced multi-scalar multiplication (MSM) algorithm for zero-knowledge provers, invented by
Karl Preisner in 2022. This repository is a clean Python reference implementation that counts
every operation, so you can see exactly where the work goes compared with other MSM algorithms.

> **Status:** work in progress. The algorithm write-up is below. The operation-counting code
> is being built now.

## Result

On BLS12-377 at 2^20 points, with the proving key precomputed once and reused across proofs,
Sagittal ran an MSM in 64 ms: 1.7× faster than every ZPrize 2022 GPU entry that runs on a V100,
and faster than all entries but one (Yrrid, 48 ms) on an A10G.

(CUDA implementation built at Sindri Labs in 2023. Measured against the
[ZPrize 2022 GPU entries](https://github.com/z-prize/2022-entries/tree/main/open-division/prize1-msm/prize1a-msm-gpu)
with the same benchmark setup: one-time setup excluded from timing for every entry.)

## The problem

Given fixed elliptic-curve points `P_1 … P_n` (a proving key that is reused for many proofs) and
new scalars `k_1 … k_n` for each proof, compute

```
Q = k_1·P_1 + k_2·P_2 + … + k_n·P_n
```

This is the most expensive step in many ZK provers, with n around 2^20 and 253-bit scalars.

## The idea

Write the scalars as rows of bits:

```
            bit:  252 ...  3  2  1  0
  k_1 · P_1   =  [  1 ...  1  0  1  0 ]
  k_2 · P_2   =  [  0 ...  0  1  0  1 ]
  k_3 · P_3   =  [  1 ...  0  1  0  1 ]
  ...
```

**Pippenger's bucket method** cuts this matrix into vertical strips that are *c bits wide and
n rows tall*. Points go into 2^c buckets by digit value, and each strip then needs a bucket
reduction step.

**Sagittal** cuts it the other way: into blocks that are *1 bit wide and g rows tall*. A block's
g bits select one of the 2^g subset sums of those g points. Because the points are fixed, every
subset sum is **precomputed once**. Each proof then only does table lookups and additions:

```
for each batch of g scalars:
    for each bit position i:
        pattern = the g bits at position i
        bucket[i] += table[batch][pattern]

result = bucket[252]
for i = 251 down to 0:
    result = 2·result + bucket[i]
```

That gives exactly one bucket per scalar bit, with no bucket reduction step, equal work per
bucket, and one writer per bucket. That structure maps very well onto GPUs. The trade-off is
memory: the table holds (2^g − 1)/g points per input point.

Sagittal combines ideas from Straus's/Shamir's simultaneous multi-exponentiation and Pippenger's
windowing. What it adds is the bit-major ("sagittal") slicing, offline subset-sum tables over a
fixed proving key, and a reduction-free parallel structure.

## What this repo will contain

- Sagittal, Pippenger (unsigned, signed, precomputed-window) and naive MSM in readable Python
- Exact counts of curve additions/doublings and field operations, split by phase
- Swappable curves: BN254, BLS12-377, a small test curve, and a fast counting group
- An analytic cost model that explains where Sagittal wins and where it stops winning

## License

[PolyForm Strict 1.0.0](LICENSE): free for noncommercial and personal use; no redistribution
or derivative works. For commercial licensing, contact Karl Preisner.

Copyright (c) 2022–2026 Karl Preisner.
