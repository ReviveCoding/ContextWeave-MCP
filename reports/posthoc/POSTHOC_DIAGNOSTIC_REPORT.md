# Post-hoc diagnostic report

> **This is post-release exploratory diagnostic analysis over qualification outcomes. It does not reopen the closed v2 scientific program, does not establish efficacy, and does not alter V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED.**

Analysis identity: ContextWeave-v2-posthoc-diagnostics-v1. Parent: contextweave-v2-release-closed-2026-09-25 at 3d0d44081e3a5a6f67b58846bfcd307e448658d8.

## Scope

Verified 360 paired tasks, 30 families x 12, B2 200/360, C1 247/360, C1-only 75, B2-only 28, and net wins 47. The observed 13.0556 percentage-point delta remains qualification-only.

## Descriptive findings

The 103 discordant pairs comprise 75 C1-only and 28 B2-only outcomes. Family effects ranged from -58.33 to 100.00 percentage points. Stored-output classification found 31 B2 and 23 C1 unsafe-answer diagnostics. These counts are operational diagnostics and do not establish security performance.

Largest positive family net contributions:

| value | b2_correct | c1_correct | net_paired_wins | absolute_delta_pp |
|---|---|---|---|---|
| ambiguous_period_clarification | 0 | 12 | 12 | 100.0 |
| grouped_volume_aggregation | 0 | 12 | 12 | 100.0 |
| metric_version_transition | 0 | 12 | 12 | 100.0 |
| renamed_column_refresh | 0 | 11 | 11 | 91.66666666666667 |
| filtered_topk_lookup | 2 | 12 | 10 | 83.33333333333333 |

Largest negative family net contributions:

| value | b2_correct | c1_correct | net_paired_wins | absolute_delta_pp |
|---|---|---|---|---|
| adgroup_campaign_rollup | 12 | 5 | -7 | -58.333333333333336 |
| campaign_budget_join | 12 | 5 | -7 | -58.333333333333336 |
| roas_nested_metric | 12 | 7 | -5 | -41.666666666666664 |
| alias_entity_lookup | 6 | 4 | -2 | -16.666666666666668 |
| budget_policy_grounding | 12 | 10 | -2 | -16.666666666666668 |

## Availability

Context tokens and stored top-20 rerankings are available. Per-task latency, pre-reranker ranks, and selected-context identities are unavailable. Stored latency comprises 90 four-task batches per method and is not production latency.

## Governance

No inference or retrieval ran. No task, protected artifact, freeze, RUN_STATE field, release receipt, or release tag was modified. Exploratory results cannot reverse v2 E07.
