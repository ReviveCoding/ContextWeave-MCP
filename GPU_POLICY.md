# GPU_POLICY.md

Physical accelerator:
NVIDIA GeForce RTX 4090 Laptop GPU

Goal:
Run expensive local neural workloads on CUDA rather than accidentally spending
hours on CPU.

Preferred architecture:

CPU preprocessing / retrieval / SQL workers
                |
                v
          bounded GPU queue
                |
                v
        ONE GPU-owner process
                |
        batched/vectorized CUDA
                |
                v
        result/evidence workers

Use GPU for:
- BGE embedding generation,
- neural reranking,
- Qwen inference,
- explicitly qualified GPU training,
- GPU-capable tree-model stages when useful.

Use CPU parallelism for:
- DuckDB,
- Polars/PyArrow,
- BM25,
- schema graphs,
- benchmark generation,
- validation,
- statistics,
- plots,
- reports.

Primary scientific comparisons must keep the inference backend fixed.

Default:
- Hugging Face deterministic inference for primary science.
- vLLM or another batching runtime only in a separately qualified systems
  experiment after scientific method selection.

Never hide CPU fallback.
Never launch several large Qwen copies on this single GPU.