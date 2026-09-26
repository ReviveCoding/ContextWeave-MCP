# Executive summary

## Decision

ContextWeave v1 and v2 both closed before any protected benchmark or scientific freeze. V1 closed as `V1_PRE_FREEZE_INSUFFICIENT_POWER`. The original v2 E07 simulation was invalidly calibrated and is preserved as `SUPERSEDED_INVALID_CALIBRATION`; a corrected, independently checked E07 analysis still found insufficient power. The final v2 identity is `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`.

## Supported evidence

The v2 qualification pilot used 360 tasks in 30 semantic families. B2 succeeded on 200/360 and C1 on 247/360. Their paired difference was +13.06 percentage points, but this is qualification evidence only. It does not support an efficacy claim. The corrected analytic calculation required 799 independent families for 0.90 power. The best feasible design at or below 600 tasks reached simulated power 0.1165.

The project also produced a validated public Criteo event audit, a controlled enterprise-style DuckDB warehouse, a semantic catalog and dependency graph, MCP transport smoke evidence, fixed-model CUDA qualification runs, and governed evidence receipts. These are separate evidence domains and do not convert the pilot into a confirmatory result.

## Boundaries

No protected task was constructed or accessed. No `DESIGN_FREEZE` or `BENCHMARK_FREEZE` exists. E08–E25 are `GATED_NOT_RUN`. There is no supported production, Amazon-internal, production-advertiser, security-certification, external-transfer, locked-performance, multi-GPU, or efficacy claim.

## Release disposition

The repository is a reproducible pre-freeze research record with a negative benchmark-design conclusion. Its defensible outcome is `INSUFFICIENT_POWER`, with the invalid simulation, corrected analysis, infrastructure interruptions, and qualification-only positive result all preserved.
