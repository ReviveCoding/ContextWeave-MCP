# Slice analysis

> **This is post-release exploratory diagnostic analysis over qualification outcomes. It does not reopen the closed v2 scientific program, does not establish efficacy, and does not alter V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED.**

Analysis identity: ContextWeave-v2-posthoc-diagnostics-v1. Parent: contextweave-v2-release-closed-2026-09-25 at 3d0d44081e3a5a6f67b58846bfcd307e448658d8.

| dimension | value | n | flag | b2_success_rate | c1_success_rate | absolute_delta_pp | net_paired_wins |
|---|---|---|---|---|---|---|---|
| expected_behavior | ABSTAIN | 12 | SMALL_SLICE | 1.0 | 1.0 | 0.0 | 0 |
| expected_behavior | ANSWER | 240 | None | 0.7125 | 0.7291666666666666 | 1.6666666666666667 | 4 |
| expected_behavior | CLARIFY | 24 | None | 0.0 | 0.5416666666666666 | 54.166666666666664 | 13 |
| expected_behavior | REFRESH | 48 | None | 0.25 | 0.7291666666666666 | 47.916666666666664 | 23 |
| expected_behavior | REFUSE | 24 | None | 0.0 | 0.0 | 0.0 | 0 |
| expected_behavior | RETRY | 12 | SMALL_SLICE | 0.4166666666666667 | 1.0 | 58.333333333333336 | 7 |
| difficulty | easy | 36 | None | 0.3333333333333333 | 1.0 | 66.66666666666667 | 24 |
| difficulty | hard | 168 | None | 0.5654761904761905 | 0.6130952380952381 | 4.761904761904762 | 8 |
| difficulty | medium | 156 | None | 0.5961538461538461 | 0.6923076923076923 | 9.615384615384615 | 15 |
| source | compositional_held_out | 96 | None | 0.6770833333333334 | 0.5208333333333334 | -15.625 | -15 |
| source | document_sql_mixed | 48 | None | 0.75 | 0.7708333333333334 | 2.0833333333333335 | 1 |
| source | independent_adversarial | 48 | None | 0.0 | 0.2708333333333333 | 27.083333333333332 | 13 |
| source | programmatic_known_answer | 96 | None | 0.7291666666666666 | 0.9166666666666666 | 18.75 | 18 |
| source | security_ood | 72 | None | 0.4027777777777778 | 0.8194444444444444 | 41.666666666666664 | 30 |
| task_mode | EXECUTABLE_SQL | 240 | None | 0.7125 | 0.7291666666666666 | 1.6666666666666667 | 4 |
| task_mode | GOVERNED_BEHAVIOR | 120 | None | 0.24166666666666667 | 0.6 | 35.833333333333336 | 43 |
| independent_review_member | False | 204 | None | 0.6323529411764706 | 0.7598039215686274 | 12.745098039215685 | 26 |
| independent_review_member | True | 156 | None | 0.4551282051282051 | 0.5897435897435898 | 13.461538461538462 | 21 |

## All semantic families

| value | n | b2_correct | c1_correct | b2_success_rate | c1_success_rate | absolute_delta_pp | c1_only | b2_only | both_wrong | discordance_rate | net_paired_wins | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| adgroup_campaign_rollup | 12 | 12 | 5 | 1.0 | 0.4166666666666667 | -58.333333333333336 | 0 | 7 | 0 | 0.5833333333333334 | -7 | SMALL_SLICE |
| alias_entity_lookup | 12 | 6 | 4 | 0.5 | 0.3333333333333333 | -16.666666666666668 | 2 | 4 | 4 | 0.5 | -2 | SMALL_SLICE |
| ambiguous_metric_clarification | 12 | 0 | 1 | 0.0 | 0.08333333333333333 | 8.333333333333334 | 1 | 0 | 11 | 0.08333333333333333 | 1 | SMALL_SLICE |
| ambiguous_period_clarification | 12 | 0 | 12 | 0.0 | 1.0 | 100.0 | 12 | 0 | 0 | 1.0 | 12 | SMALL_SLICE |
| bid_policy_grounding | 12 | 12 | 12 | 1.0 | 1.0 | 0.0 | 0 | 0 | 0 | 0.0 | 0 | SMALL_SLICE |
| budget_policy_grounding | 12 | 12 | 10 | 1.0 | 0.8333333333333334 | -16.666666666666668 | 0 | 2 | 0 | 0.16666666666666666 | -2 | SMALL_SLICE |
| cache_version_validation | 12 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0 | 0 | 12 | 0.0 | 0 | SMALL_SLICE |
| campaign_advertiser_join | 12 | 8 | 12 | 0.6666666666666666 | 1.0 | 33.333333333333336 | 4 | 0 | 0 | 0.3333333333333333 | 4 | SMALL_SLICE |
| campaign_budget_join | 12 | 12 | 5 | 1.0 | 0.4166666666666667 | -58.333333333333336 | 0 | 7 | 0 | 0.5833333333333334 | -7 | SMALL_SLICE |
| cpa_ratio_metric | 12 | 12 | 12 | 1.0 | 1.0 | 0.0 | 0 | 0 | 0 | 0.0 | 0 | SMALL_SLICE |
| cross_tenant_refusal | 12 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0 | 0 | 12 | 0.0 | 0 | SMALL_SLICE |
| ctr_ratio_metric | 12 | 12 | 12 | 1.0 | 1.0 | 0.0 | 0 | 0 | 0 | 0.0 | 0 | SMALL_SLICE |
| distractor_table_collision | 12 | 12 | 12 | 1.0 | 1.0 | 0.0 | 0 | 0 | 0 | 0.0 | 0 | SMALL_SLICE |
| document_sql_dependency | 12 | 12 | 12 | 1.0 | 1.0 | 0.0 | 0 | 0 | 0 | 0.0 | 0 | SMALL_SLICE |
| entity_status_lookup | 12 | 12 | 12 | 1.0 | 1.0 | 0.0 | 0 | 0 | 0 | 0.0 | 0 | SMALL_SLICE |
| filtered_topk_lookup | 12 | 2 | 12 | 0.16666666666666666 | 1.0 | 83.33333333333333 | 10 | 0 | 0 | 0.8333333333333334 | 10 | SMALL_SLICE |
| governed_schema_alias | 12 | 0 | 3 | 0.0 | 0.25 | 25.0 | 3 | 0 | 9 | 0.25 | 3 | SMALL_SLICE |
| grouped_volume_aggregation | 12 | 0 | 12 | 0.0 | 1.0 | 100.0 | 12 | 0 | 0 | 1.0 | 12 | SMALL_SLICE |
| keyword_campaign_multihop | 12 | 0 | 1 | 0.0 | 0.08333333333333333 | 8.333333333333334 | 1 | 0 | 11 | 0.08333333333333333 | 1 | SMALL_SLICE |
| metric_version_transition | 12 | 0 | 12 | 0.0 | 1.0 | 100.0 | 12 | 0 | 0 | 1.0 | 12 | SMALL_SLICE |
| missing_dependency_abstention | 12 | 12 | 12 | 1.0 | 1.0 | 0.0 | 0 | 0 | 0 | 0.0 | 0 | SMALL_SLICE |
| missing_scope_refusal | 12 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0 | 0 | 12 | 0.0 | 0 | SMALL_SLICE |
| policy_dependency_multihop | 12 | 11 | 9 | 0.9166666666666666 | 0.75 | -16.666666666666668 | 0 | 2 | 1 | 0.16666666666666666 | -2 | SMALL_SLICE |
| renamed_column_refresh | 12 | 0 | 11 | 0.0 | 0.9166666666666666 | 91.66666666666667 | 11 | 0 | 1 | 0.9166666666666666 | 11 | SMALL_SLICE |
| roas_nested_metric | 12 | 12 | 7 | 1.0 | 0.5833333333333334 | -41.666666666666664 | 0 | 5 | 0 | 0.4166666666666667 | -5 | SMALL_SLICE |
| rolling_window_peak | 12 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0 | 0 | 12 | 0.0 | 0 | SMALL_SLICE |
| stale_watermark_refresh | 12 | 12 | 12 | 1.0 | 1.0 | 0.0 | 0 | 0 | 0 | 0.0 | 0 | SMALL_SLICE |
| temporal_period_aggregation | 12 | 12 | 11 | 1.0 | 0.9166666666666666 | -8.333333333333334 | 0 | 1 | 0 | 0.08333333333333333 | -1 | SMALL_SLICE |
| temporal_period_comparison | 12 | 12 | 12 | 1.0 | 1.0 | 0.0 | 0 | 0 | 0 | 0.0 | 0 | SMALL_SLICE |
| transient_retry_contract | 12 | 5 | 12 | 0.4166666666666667 | 1.0 | 58.333333333333336 | 7 | 0 | 0 | 0.5833333333333334 | 7 | SMALL_SLICE |

Exact McNemar p values and BH q values are exploratory. Slices below 20 or with fewer than 10 discordant pairs were not tested.

| dimension | value | n | mcnemar_exact_p | bh_fdr_q |
|---|---|---|---|---|
| family | ambiguity_clarification | 24 | 0.000244140625 | 0.000518798828125 |
| family | lookup | 36 | 0.076812744140625 | 0.09327261788504464 |
| family | multi_table_join | 36 | 0.0308837890625 | 0.04038649338942308 |
| expected_behavior | ANSWER | 240 | 0.6988834276200058 | 0.6988834276200058 |
| expected_behavior | CLARIFY | 24 | 0.000244140625 | 0.000518798828125 |
| expected_behavior | REFRESH | 48 | 2.384185791015625e-07 | 1.0132789611816406e-06 |
| difficulty | easy | 36 | 1.1920928955078125e-07 | 6.755193074544271e-07 |
| difficulty | hard | 168 | 0.26818725105476915 | 0.30394555119540506 |
| difficulty | medium | 156 | 0.023702702470473014 | 0.03357882849983677 |
| source | compositional_held_out | 96 | 0.0014896392822265625 | 0.0028137630886501735 |
| source | independent_adversarial | 48 | 0.000244140625 | 0.000518798828125 |
| source | programmatic_known_answer | 96 | 0.0029350556433200836 | 0.0049895945936441425 |
| source | security_ood | 72 | 1.862645149230957e-09 | 1.5832483768463135e-08 |
| task_mode | EXECUTABLE_SQL | 240 | 0.6988834276200058 | 0.6988834276200058 |
| task_mode | GOVERNED_BEHAVIOR | 120 | 2.2737367544323206e-13 | 3.865352482534945e-12 |
| independent_review_member | False | 204 | 0.00337223333414807 | 0.005211633334592472 |
| independent_review_member | True | 156 | 0.00010371580719947815 | 0.0003526337444782257 |
