# Resume-safe evidence

These bullets describe implemented work and qualification evidence. They do not claim confirmatory lift, production deployment, Amazon-internal use, security certification, or external transfer.

- Built a reproducible, single-GPU research pipeline over 16.47 million public Criteo event rows and a controlled 36-table enterprise-style DuckDB warehouse, with source hashes, provenance, semantic metrics, dependency closure, and MCP stdio/HTTP smoke validation.
- Implemented resumable CUDA qualification for Qwen3-4B, BGE-M3, and BGE reranking across a 360-task, 30-family benchmark; preserved paired B2/C1 outcomes and correctly labeled the observed +13.06 percentage-point difference as qualification-only.
- Audited and corrected an anti-calibrated clustered power simulation, independently validated its null behavior with 100,000 replicates, and closed the study pre-freeze when the corrected design required 799 families and no design within 600 tasks reached target power.

Scientific disposition: v1 `V1_PRE_FREEZE_INSUFFICIENT_POWER`; original v2 E07 `SUPERSEDED_INVALID_CALIBRATION`; corrected v2 `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`. No protected benchmark was created or accessed.
