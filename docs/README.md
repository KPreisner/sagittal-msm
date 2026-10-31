# Sagittal MSM docs

1. [Multi-scalar multiplication](1-msm.md): the problem, what curve operations cost, the naive
   way.
2. [Pippenger's bucket method](2-pippenger.md): windows, buckets, signed digits, precomputed
   windows.
3. [Sagittal MSM](3-sagittal.md): the algorithm, a worked example, the one-add table build, costs,
   and how it relates to known methods.
4. [Why Sagittal suits GPUs](4-gpu.md): the shape of its work, the CUDA kernel, and the memory
   limit.
5. [Results](5-results.md): 2023 GPU timings, operation counts, field-weighted costs,
   precompute, and memory.
6. [Methodology](6-methodology.md): how the counts and model are produced and tested, and what
   they don't cover.
