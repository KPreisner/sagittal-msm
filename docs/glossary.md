# Terms and references

[Docs index](README.md)

**Field, field element, field multiplication.** The numbers 0 to p − 1, where adding,
subtracting, multiplying and dividing all wrap around modulo the prime p. A field element is one
such number; a field multiplication multiplies two of them mod p. Curve coordinates are field
elements. See [1. MSM](1-msm.md).

**Scalar field r vs base field p.** Coordinates are numbers mod p (377 bits for BLS12-377). The
curve has h·r points; provers use the subgroup of prime order r (253 bits), so scalars only matter
mod r. A prime order means every point but O generates the subgroup and the discrete logarithm
gets the full difficulty of r ([Pohlig–Hellman](https://en.wikipedia.org/wiki/Pohlig%E2%80%93Hellman_algorithm)). See [1. MSM](1-msm.md).

**Sagittal plane.** In anatomy, the vertical plane that divides a body into left and right halves
([Wikipedia](https://en.wikipedia.org/wiki/Sagittal_plane)). Sagittal MSM is named for its
slicing: it cuts the scalar bit matrix into columns one bit wide, where Pippenger cuts strips c
bits wide. See [4. Sagittal](4-sagittal.md).

**Identity point O, and −P.** The curve's "zero": P + O = P. The negative of P = (x, y) is
−P = (x, −y), and P + (−P) = O.

**Circuit, proving key.** A circuit is the computation being proved, written as arithmetic
constraints. The proving key is the fixed set of curve points (from a one-time setup) that every
proof of that circuit uses. Those points are the P_i of the MSM.

**Affine, Jacobian, XYZZ.** Ways to store a point (formulas in the [Explicit-Formulas Database](https://hyperelliptic.org/EFD/g1p/auto-shortw.html)). Affine is plain (x, y). Jacobian is (X, Y, Z)
with x = X/Z², y = Y/Z³. XYZZ is (X, Y, ZZ, ZZZ) with x = X/ZZ, y = Y/ZZZ. The last two avoid
division until the end. See [1. MSM](1-msm.md).

**Mixed add, full add, double.** Adding a stored affine point to a running sum; adding two
running sums; adding a point to itself.

**Montgomery form, CIOS.** Storing a as a·R mod p so that reducing mod p needs no division; CIOS
is the standard way to compute one Montgomery multiplication ([Wikipedia](https://en.wikipedia.org/wiki/Montgomery_modular_multiplication);
CIOS is from [Koç, Acar and Kaliski, 1996](https://doi.org/10.1109/40.502403)). See
[2. Big numbers and GPUs](2-hardware.md).

**Kernel, thread block, warp, atomic add.** A kernel is a program that runs on the GPU. Its
threads are grouped into blocks (up to 1,024 threads sharing fast on-chip memory) and warps
(32 threads running one instruction together). An atomic add is a hardware instruction that lets
many threads add to the same number without losing updates; it works on single machine numbers,
not on curve points. See [2. Big numbers and GPUs](2-hardware.md) and the [CUDA programming guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/).

**n, b, c, g.** n is the number of points (and scalars) in the MSM. b is the number of scalar
bits (253 for BLS12-377). c is Pippenger's window width in bits. g is Sagittal's batch size:
points per precomputed table.

**Bucket, table entry.** A bucket is a running sum of points. In Pippenger there is one per
possible digit value per window; in Sagittal, one per scalar bit. A table entry is one
precomputed subset sum of a batch's points.

**Signed digits.** Window digits from −(2^(c−1) − 1) to 2^(c−1) instead of 0 to 2^c − 1. A
negative digit adds −P, which is nearly free (flipping the sign of y is one field subtraction), so
each window needs half as many buckets: 2^(c−1) instead of 2^c. See [3. Pippenger](3-pippenger.md).

**Horner's rule.** Combining buckets from the top: result = 2·result + bucket[i], down to bit 0,
the same doubling chain as double-and-add with bucket i in place of P ([Wikipedia](https://en.wikipedia.org/wiki/Horner%27s_method)).

**Straus's method (Shamir's trick).** Computing k1·P1 + … + kg·Pg by precomputing all 2^g subset
sums and running one double-and-add over all g scalars together. One Sagittal batch is exactly
this. Straus gave it as the solution to [Problem 5125](https://doi.org/10.2307/2310929) (Bellman
and Straus, *American Mathematical Monthly*, 1964); the same idea appears in
[ElGamal's 1985 signature paper](https://doi.org/10.1109/TIT.1985.1057074). Textbook treatment:
[Handbook of Applied Cryptography, §14.6](https://cacr.uwaterloo.ca/hac/about/chap14.pdf). See
[4. Sagittal](4-sagittal.md).

**Yrrid configuration.** This project's model of the parameters Yrrid used in its winning ZPrize
2022 entry: window c = 23, signed digits, and shifted point copies that fold all windows into
2 bucket sets. It counts that algorithm's operations; it is not Yrrid's code.

**ZPrize.** A 2022 competition to accelerate zero-knowledge proving. Its GPU MSM track
(BLS12-377, batches of 2^26 points) was led by Yrrid and MatterLabs, whose entries were later
combined into one: [challenge](https://www.zprize.io/prizes/accelerating-msm-operations-on-gpu-fpga), [results](https://www.zprize.io/blog/announcing-zprize-results), [entries](https://github.com/z-prize/2022-entries/tree/main/open-division/prize1-msm/prize1a-msm-gpu), [Yrrid's code](https://github.com/yrrid/submission-msm-gpu).

**BLS12-377, BN254, Goldilocks.** [BLS12-377](https://eips.ethereum.org/EIPS/eip-2539) (introduced in the [Zexe paper](https://eprint.iacr.org/2018/962)) and [BN254](https://eips.ethereum.org/EIPS/eip-197) are curves widely used in zero-knowledge
proofs (377- and 254-bit fields; 253- and 254-bit scalars). Goldilocks is the prime
2^64 − 2^32 + 1, popular because its numbers fit in a 64-bit word (used by [Plonky2](https://github.com/0xPolygonZero/plonky2)); this project uses a small test
curve over it.

**V100, A10G, Ampere, sppark.** The V100 (2017, Volta generation, 16 GB) and A10G (Ampere
generation, 24 GB) are NVIDIA GPUs. Ampere is the 2020 generation; Yrrid's code requires it.
[sppark](https://github.com/supranational/sppark) is Supranational's open-source GPU library for MSMs and field arithmetic; Sindri's kernel
used its field and point types.


## Further reading

- [Sagittal MSM: a streamlined MSM implementation](https://medium.com/@sindrilabs/sagittal-msm-a-streamlined-msm-implementation-a9dcc07da585) (the 2023 write-up)
- [Pippenger's exponentiation algorithm](https://cr.yp.to/papers/pippenger.pdf) (Bernstein's notes)
- [Explicit-Formulas Database](https://hyperelliptic.org/EFD/g1p/auto-shortw.html) (every curve-arithmetic formula, with costs)
- [Montgomery modular multiplication](https://en.wikipedia.org/wiki/Montgomery_modular_multiplication) (including CIOS)
- ZPrize MSM: [challenge](https://www.zprize.io/prizes/accelerating-msm-operations-on-gpu-fpga), [results](https://www.zprize.io/blog/announcing-zprize-results), [entries](https://github.com/z-prize/2022-entries/tree/main/open-division/prize1-msm/prize1a-msm-gpu)
- FPGA MSM designs: PipeMSM ([eprint 2022/999](https://eprint.iacr.org/2022/999)) and CycloneMSM ([eprint 2022/1396](https://eprint.iacr.org/2022/1396))
- [sppark](https://github.com/supranational/sppark) (Supranational's GPU MSM library)

[Docs index](README.md)
