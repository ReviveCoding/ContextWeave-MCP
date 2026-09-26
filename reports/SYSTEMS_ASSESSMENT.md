# Systems assessment

## Executed qualification work

The project used one NVIDIA GeForce RTX 4090 Laptop GPU for local neural qualification. The Codex reasoning model was remote and did not run on that GPU. B2 and C1 used Qwen3-4B revision `1cfa9a7208912126459214e8b04321603b3df60c`, Transformers, bfloat16, CUDA, and batch size 4. B2 reported peak allocated VRAM 9,059,802,624 bytes; C1 reported 8,776,676,352 bytes. These are qualification runtime records rather than systems benchmarks.

BGE-M3 and BGE-reranker-v2-m3 retrieval artifacts were validated for all 360 task identities. MCP in-memory, stdio, and Streamable HTTP smoke checks passed for the implemented eight-tool surface and protocol version 2026-07-28.

## Environment recovery

The Windows-mounted `.venv` became incomplete after reboot: `torch` imported as a namespace without `Tensor` or `LongTensor`. Release closure recreates the locked environment at `/home/bjw-0/.cache/contextweave-mcp/venv` with uv frozen resolution and copy semantics. The NVIDIA driver and system CUDA installation are left unchanged.

## Unexecuted systems evidence

E21 cold/warm latency experiments, transport latency distributions, p50/p95 end-to-end latency, TTFT, token efficiency, cache latency, GPU energy, alternate runtime comparisons, and multi-process serving are `NOT RUN / GATED`. No production throughput, availability, latency, distributed, or multi-GPU claim is supported.

## Scientific boundary

V1 closed pre-freeze for insufficient power. The original v2 E07 was invalidly calibrated and preserved as superseded; corrected E07 was calibrated and still insufficiently powered. No protected benchmark or freeze exists. The +13.06 percentage-point result is qualification-only and is not a systems or efficacy claim.
