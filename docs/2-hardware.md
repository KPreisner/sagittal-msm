# 2. Big numbers and GPUs

[Docs index](README.md) · Previous: [1. MSM](1-msm.md) · Next: [3. Pippenger](3-pippenger.md)

Counting curve operations is only half the story. This page covers what one operation costs in
hardware, and why GPUs reward some algorithms over others.

## Numbers bigger than a machine word

A **machine word** is the size of number a processor handles in one instruction: **64 bits** on a
modern CPU and **32 bits** for a GPU's integer units. A 64-bit word holds numbers up to about
1.8 × 10¹⁹. A 377-bit field element is far bigger (up to about 10¹¹³), so it is stored as an
array of words, called limbs: 6 words on a CPU, **12 on a GPU**.

Arithmetic then happens word by word, like long multiplication on paper:

![A 377-bit multiplication as 32-bit word products](figures/limbs.png)

- **Multiplying** two 12-word numbers takes 12 × 12 = 144 word multiplications, with carries
  passed from each partial product to the next.
- **Reducing** the 24-word product mod p brings it back to 12 words. Done directly, that means
  dividing a 754-bit number by a 377-bit one and keeping the remainder: a long division, far
  slower than the multiplication itself.
- **[Montgomery form](https://en.wikipedia.org/wiki/Montgomery_modular_multiplication)** avoids that division. Instead of a, store a·R mod p, with R = 2³⁸⁴ (the
  first power of 2 above every 12-word number). Multiplying two stored values gives
  (aR)(bR) = abR²; turning that back into the stored form of ab, abR, means dividing by R once.
  R is a power of 2, so dividing by it just drops the low words. A few extra multiplications
  make sure that division is exact. Values are converted into Montgomery form once at the
  start and out once at the end; everything in between stays in it. Sindri's GPU code kept
  every field element in Montgomery form.
- **CIOS** (Coarsely Integrated Operand Scanning, [Koç, Acar and Kaliski, 1996](https://doi.org/10.1109/40.502403)) is the most common
  way to compute one Montgomery multiplication. It interleaves multiplying and reducing word by
  word, so the running result never grows past 14 words. It takes 2s² + s word multiply-adds
  for s words: **300 for s = 12**, about twice the 144 of the plain product.
- **A curve operation multiplies that again.** A mixed add is 10 field multiplications, so about
  **3,000 word multiply-adds**, plus additions and carry handling.

The sizes add up in memory too. On BLS12-377:

| Value | Words (32-bit) | Bytes |
|---|---|---|
| Scalar | 8 | 32 |
| Affine point (x, y) | 24 | 96 |
| XYZZ accumulator (X, Y, ZZ, ZZZ) | 48 | 192 |
| 2^20 input points | | 96 MiB |

## A GPU in brief

A GPU program is called a **kernel** ([CUDA programming guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)). It runs as thousands of threads, organized two ways:
**thread blocks** of up to 1,024 threads that share fast on-chip memory and can wait for each
other, and **warps** of 32 threads. A warp executes one instruction at a time for all 32 threads
together. If threads in a warp need to do different
things (an `if` that goes different ways, or loops of different length), the warp runs each path
in turn while the other threads wait. This is called **divergence**.

Memory comes in tiers, from small and fast to large and slow:

```mermaid
flowchart LR
    R["Registers<br/>up to 255 × 32-bit per thread<br/>fastest"] --> S["Shared memory<br/>48 KB per block by default<br/>on-chip"]
    S --> G["Global memory<br/>16–48 GB (V100–A40)<br/>~100s of cycles away"]
    G --> H["Host (CPU) memory<br/>over PCIe<br/>slowest"]
```

- **Registers.** One XYZZ accumulator takes 48 of a thread's 255 registers, and an addition
  needs several temporaries on top. The more registers each thread uses, the fewer threads fit
  on the chip at once, and the less the GPU can hide memory delays by switching between them.
- **Shared memory.** Small, fast, and shared by the threads of one block. It is the natural place
  for data many threads read, like Sagittal's per-batch tables: 48 KB holds a table for g ≤ 9.
- **Global memory.** Large but slow. It holds the points, scalars and precomputed data. At large
  n it fills up: on a 16 GiB V100, the points and scalars for 2^26 points alone take 8.6 GB.

## Why data-dependent work is costly on a GPU

In Pippenger's bucket method ([next page](3-pippenger.md)), the bucket a point goes to depends on
its scalar. Whatever the GPU does with that, it costs something:

- **Thousands of threads may target the same bucket.** Adding into a bucket is a curve addition
  (about 3,000 multiply-adds), not a single instruction, so the hardware's **atomic add** (an
  instruction that lets many threads add to the same number without losing updates) can't do
  it. Threads have to take a lock (and wait in line), or the work has to be rearranged first.
- **Rearranging means sorting.** Fast implementations first sort points by bucket, so each bucket's
  points are processed together. That is extra full passes over memory, every proof.
- **Bucket sizes are uneven.** Some buckets get many more points than others. Threads in a warp
  that finish early wait for the slowest, so implementations sort or split buckets by size to
  balance the work. Yrrid, the ZPrize 2022 winner, sorted buckets so the largest run first.
- **Reduction waits for accumulation.** Combining buckets can only start once every bucket is
  final, which adds a synchronization point and a second phase of work.

These queues, sorts and schedulers work. The ZPrize winners do them very well and are fastest at
large n. But they are overhead: memory traffic, synchronization and code. An algorithm whose work
is fixed in advance doesn't pay them.

```mermaid
flowchart TB
    subgraph pip["Pippenger: work depends on the data"]
        direction LR
        A1["scalars"] --> A2["digits"] --> A3["sort points<br/>by bucket"] --> A4["accumulate<br/>(uneven buckets)"] --> A5["reduce<br/>buckets"]
    end
    subgraph sag["Sagittal: work fixed in advance"]
        direction LR
        B1["scalars"] --> B2["bit patterns"] --> B3["accumulate<br/>(one bucket per bit,<br/>equal loads)"] --> B4["combine 253<br/>buckets on CPU"]
    end
```

[Docs index](README.md) · Previous: [1. MSM](1-msm.md) · Next: [3. Pippenger](3-pippenger.md)
