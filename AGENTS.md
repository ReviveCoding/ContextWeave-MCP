# AGENTS.md — ContextWeave-MCP

## Authority

MASTER_PROMPT.md is the authoritative scientific and implementation
specification for this repository.

Read MASTER_PROMPT.md and GPU_POLICY.md completely before substantive work.

## Paths

Windows repository:

    C:\Users\bjw-0\Downloads\ContextWeave-MCP

WSL repository:

    /mnt/c/Users/bjw-0/Downloads/ContextWeave-MCP

High-I/O WSL native scratch:

    /home/bjw-0/.cache/contextweave-mcp

WSL distro:

    Ubuntu-22.04

Local accelerator:

    NVIDIA GeForce RTX 4090 Laptop GPU

## Important distinction

The Codex reasoning model is remote.

The RTX 4090 is for LOCAL project computation such as:
- Qwen inference,
- embeddings,
- neural reranking,
- GPU-capable model training,
- GPU-capable tree models when justified,
- serving and systems benchmarks.

Never claim Codex itself runs on the RTX GPU.

## GPU-first policy

For expensive neural/model workloads:
1. qualify CUDA first;
2. use CUDA when the scientific design supports it;
3. do not silently fall back to CPU;
4. fail closed if a GPU-designated final experiment accidentally runs on CPU;
5. record device, dtype, backend, model revision, batch size, timing and VRAM.

## One physical GPU

There is one physical GPU.

Use:
- CPU producer workers,
- a bounded GPU work queue,
- one long-lived GPU-owner process,
- large/vectorized GPU batches,
- CPU result/evidence workers.

Do not launch multiple competing large-model processes merely to claim
parallelism.

Parallel Codex subagents may work on independent web research, coding, tests,
reviews, documentation and CPU analyses. They must not launch independent
VRAM-heavy jobs.

## Filesystem

Final project source, compact evidence, reports, figures, configs and
reproducibility artifacts belong in the Windows repository.

High-I/O model caches, temporary datasets, temporary Parquet, temporary model
artifacts and GPU staging should use the native WSL scratch directory.

If a WSL scratch write requires permission escalation, use the normal
Approve-for-me flow rather than falling back to slow CPU or Windows-mounted
scratch.

## Scientific discipline

- Never fabricate metrics or PASS states.
- Never turn an unexecuted experiment into evidence.
- Preserve negative and null results.
- Preserve failed protocol identities.
- Keep public, controlled-synthetic, qualification, locked, exploratory and
  external evidence separate.
- Do not retune after protected outcome access.
- Complexity must earn promotion against strong baselines.
- Do not turn public or synthetic ad data into production-advertiser claims.
- Do not turn one-GPU work into distributed-performance claims.

## Run management

Maintain:
    RUN_STATE.json
    NEXT_ACTION.md

Every long-running stage must be restartable and idempotent.

For deterministic long jobs, prefer one blocking/supervisor process with durable
logs and receipts. Do not repeatedly wake Codex only to poll an unchanged
long-running job.

## Git

Local commits and scientific freeze tags are allowed.

Do not push, publish, create a public repository, or upload artifacts to
external services without explicit authorization.
