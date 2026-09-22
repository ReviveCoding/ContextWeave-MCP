# V2 blind-review integration

The blind reviewer authored eight construct specifications without reading candidate-method source, pilot outcomes, or v1 family effects. All eight were accepted subject to their stated generation gates. The normative review artifacts are `benchmarks/v2_independent_adversarial_families.json` and `reports/V2_INDEPENDENT_REVIEW.md`.

The qualification compiler maps 13 of its 30 semantic families to all eight independently reviewed constructs:

| Blind construct | Implemented qualification families |
|---|---|
| Ambiguity/clarification | `ambiguous_metric_clarification`, `ambiguous_period_clarification` |
| Authorization/refusal | `missing_scope_refusal`, `cross_tenant_refusal` |
| Freshness action | `stale_watermark_refresh` |
| Schema drift recovery | `renamed_column_refresh` |
| Distractor-table stress | `distractor_table_collision` |
| Document + SQL | `document_sql_dependency`, `budget_policy_grounding`, `bid_policy_grounding` |
| Cache sequence validity | `cache_version_validation` |
| Multi-hop dependency closure | `keyword_campaign_multihop`, `policy_dependency_multihop` |

Each task records `independent_review_family` so the lineage is machine-auditable. The remaining 17 families were designed from the authoritative project specification and are not represented as independently authored.

This pilot implements single-turn cache and freshness qualification cases. It does not claim to satisfy the reviewer's full stateful sequence gate for a protected benchmark. If v2 reaches a freeze, protected cache families must use clean-state sequence replay, transition-aware cache keys, and trace-level exposure checks. Authorization remains a zero-tolerance hard gate in any protected design.
