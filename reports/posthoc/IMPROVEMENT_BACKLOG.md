# Improvement backlog

> **This is post-release exploratory diagnostic analysis over qualification outcomes. It does not reopen the closed v2 scientific program, does not establish efficacy, and does not alter V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED.**

Analysis identity: ContextWeave-v2-posthoc-diagnostics-v1. Parent: contextweave-v2-release-closed-2026-09-25 at 3d0d44081e3a5a6f67b58846bfcd307e448658d8.

Impact equals frequency x severity x confidence. Subsystem assignments are hypotheses, not causal findings. Every mitigation requires a new scientific protocol.

| issue | frequency | severity | confidence | impact | likely_subsystem | affected_slice_count | evidence | proposed_mitigation | requires_new_scientific_protocol |
|---|---|---|---|---|---|---|---|---|---|
| RETRIEVAL_COVERAGE_ASSOCIATION | 100 | 3 | 0.5 | 150.0 | retrieval | 13 | required IDs absent from stored top-20 on failed tasks | Add exact dependency injection, then test in a new protocol. | True |
| UNSAFE_ANSWER | 23 | 5 | 1.0 | 115.0 | behavior_control | 2 | stored C1 status and behavior fields | Gate executable output by expected behavior. | True |
| SQL_EXECUTION_ERROR | 24 | 4 | 1.0 | 96.0 | sql_execution | 7 | stored C1 status and behavior fields | Audit identifiers and sandbox-compatible SQL. | True |
| WRONG_DEFERRAL | 25 | 3 | 1.0 | 75.0 | behavior_control | 3 | stored C1 status and behavior fields | Improve exact deferral routing. | True |
| WRONG_RESULT | 18 | 4 | 1.0 | 72.0 | sql_generation | 5 | stored C1 status and behavior fields | Add targeted join and aggregation qualification. | True |
| OVER_REFUSAL | 23 | 3 | 1.0 | 69.0 | behavior_control | 4 | stored C1 status and behavior fields | Improve answerability without weakening policy gates. | True |
