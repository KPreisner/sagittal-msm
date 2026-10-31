# Sagittal MSM docs

The same material as an interactive walkthrough: [karl.preisner.us/sagittal-msm](https://karl.preisner.us/sagittal-msm/).

1. [MSM and elliptic-curve arithmetic](1-msm.md): a dot product of points, how points are added,
   why there is no multiply, double-and-add.
2. [Big numbers and GPUs](2-hardware.md): 377-bit arithmetic on 32-bit hardware, GPU memory tiers,
   and why data-dependent work is costly on a GPU.
3. [Pippenger's bucket method](3-pippenger.md): windows, buckets, signed digits, precomputed
   windows.
4. [Sagittal MSM](4-sagittal.md): the algorithm, a worked example, the one-add table build, costs,
   and how it relates to known methods.
5. [Why Sagittal suits GPUs](5-gpu.md): design goals, the shape of its work, the CUDA kernel, and
   the memory limit.
6. [Results](6-results.md): 2023 GPU timings, operation counts, field-weighted costs,
   precompute, and memory.
7. [Methodology](7-methodology.md): how the counts and model are produced and tested, and what
   they don't cover.
