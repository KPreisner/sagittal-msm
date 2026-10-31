# 1. MSM and elliptic-curve arithmetic

[Docs index](README.md) · Next: [2. Big numbers and GPUs](2-hardware.md)

## A dot product

A dot product multiplies two lists pairwise and adds up the results:

```
(3, 5, 2) · (4, 1, 7) = 3·4 + 5·1 + 2·7 = 12 + 5 + 14 = 31
```

A **multi-scalar multiplication (MSM)** has the same shape, except the second list holds
elliptic-curve points instead of numbers:

```
(k_1, k_2, …, k_n) · (P_1, P_2, …, P_n) = k_1·P_1 + k_2·P_2 + … + k_n·P_n
```

The k_i are **scalars**: ordinary integers, about 253 bits long. The P_i are **points**: pairs
(x, y) of 377-bit numbers that satisfy a curve equation. MSMs are the most expensive step in
many zero-knowledge provers (Groth16, PLONK and KZG commitments), with n in the millions.

Two properties of the real workload shape everything that follows:

- **The points are fixed.** They come from the proving key (the common reference string), which
  is the same for every proof of a given circuit. Anything computed from the points alone can
  be computed once and reused.
- **The scalars change every proof.** They come from the witness, so per-proof work is what
  matters.

## Adding two points

The curves used here have the equation y² = x³ + b: b = 1 for BLS12-377 and b = 3 for BN254.
Points on a curve can be added, and the rule has a picture. Over the real numbers, draw the line
through P and Q; it meets the curve at exactly one more point; reflect that point across the
x-axis, and the result is P + Q.

![Adding two points on an elliptic curve, step by step](figures/ec_add.gif)

In coordinates, with λ the slope of the line:

```
λ  = (y₂ − y₁) / (x₂ − x₁)
x₃ = λ² − x₁ − x₂
y₃ = λ(x₁ − x₃) − y₁
```

Adding a point to itself (doubling) uses the tangent line instead, with slope λ = 3x₁² / (2y₁).

![Adding and doubling points](figures/ec_add.png)

Real curves use the same formulas with every number taken modulo a large prime p (377 bits for
BLS12-377). There the picture becomes a scatter of points, but the algebra is identical. There is
also an identity point O (the "point at infinity"): P + O = P, and P + (−P) = O, where −P = (x, −y).

**Division is the expensive part.** Modulo p, dividing means multiplying by an inverse, and an
inverse costs hundreds of multiplications. So implementations keep a running denominator in
extra coordinates (Jacobian, XYZZ) and divide only once at the very end. That turns one addition
into about 10–16 field multiplications:

| Operation | What it is | Field multiplications (XYZZ) | (Jacobian) |
|---|---|---|---|
| Mixed add | accumulator + a stored, normalized point | 10 | 11 |
| Full add | accumulator + accumulator | 14 | 16 |
| Double | 2 × accumulator | 9 | 7 |

Counts are multiplications plus squarings from the
[Explicit-Formulas Database](https://hyperelliptic.org/EFD/g1p/auto-shortw.html) formulas this
repo implements, and the tests check every one against measured field operations. XYZZ is what the
fastest GPU MSMs use.

```mermaid
flowchart LR
    F["Field ops<br/>mul, sqr, add mod p"] --> E["Curve ops<br/>add, mixed add, double"]
    E --> S["Scalar multiplication<br/>k·P"]
    S --> M["MSM<br/>Σ k_i·P_i"]
```

## There is no multiply

A curve has **only addition**. "k·P" is shorthand for adding P to itself k times:

```
5·P = P + P + P + P + P
```

There is no instruction that multiplies a point by a number, and no way to multiply two points
together. Going backwards, recovering k from k·P, is the discrete logarithm problem. It is
believed infeasible for these curves, and that is what makes them useful for cryptography.

Adding P to itself 2²⁵³ times is impossible, so scalar multiplication uses **double-and-add**:
read k's bits from the top, double at every bit and add P at every 1 bit. For k = 13 = 1101 in
binary:

| bit | step | value |
|---|---|---|
| 1 | start | P |
| 1 | double, add P | 2P + P = 3P |
| 0 | double | 6P |
| 1 | double, add P | 12P + P = 13P |

That is 3 doublings and 2 additions instead of 12 additions. A 253-bit scalar takes about
252 doublings and 126 additions: **376 curve operations per point**, measured.

## The naive MSM

Do one double-and-add per point, then add up the n results: about 376·n curve operations. At
n = 2^20 that is about 400 million curve operations, each costing 10–16 field multiplications.
Each of those is itself hundreds of machine instructions, as the [next page](2-hardware.md)
shows.

A useful way to see the fixed points: in a KZG-style setup, `P_i = τ^i·G` for a secret τ, so an
MSM with coefficients `c_i` evaluates a polynomial "in the exponent":

```
Σ c_i·(τ^i·G) = (Σ c_i·τ^i)·G = P(τ)·G
```

The prover computes `P(τ)·G` without ever learning τ. The original 2022 prototype of Sagittal
checked its answers exactly this way: evaluate `P(τ)` in the clear with the secret, then compare.

[Docs index](README.md) · Next: [2. Big numbers and GPUs](2-hardware.md)
