# Error analysis

> **This is post-release exploratory diagnostic analysis over qualification outcomes. It does not reopen the closed v2 scientific program, does not establish efficacy, and does not alter V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED.**

Analysis identity: ContextWeave-v2-posthoc-diagnostics-v1. Parent: contextweave-v2-release-closed-2026-09-25 at 3d0d44081e3a5a6f67b58846bfcd307e448658d8.

Taxonomy uses stored fields only; hidden reasoning and causal mechanisms are not inferred.

| method | error_type | count | rate |
|---|---|---|---|
| B2 | CORRECT | 200 | 0.5555555555555556 |
| B2 | OVER_REFUSAL | 5 | 0.013888888888888888 |
| B2 | SQL_EXECUTION_ERROR | 40 | 0.1111111111111111 |
| B2 | UNSAFE_ANSWER | 31 | 0.08611111111111111 |
| B2 | WRONG_DEFERRAL | 60 | 0.16666666666666666 |
| B2 | WRONG_RESULT | 24 | 0.06666666666666667 |
| C1 | CORRECT | 247 | 0.6861111111111111 |
| C1 | OVER_REFUSAL | 23 | 0.06388888888888888 |
| C1 | SQL_EXECUTION_ERROR | 24 | 0.06666666666666667 |
| C1 | UNSAFE_ANSWER | 23 | 0.06388888888888888 |
| C1 | WRONG_DEFERRAL | 25 | 0.06944444444444445 |
| C1 | WRONG_RESULT | 18 | 0.05 |

Unsafe answers are operationally critical diagnostics, not security certification.

| method | expected | observed | diagnostic | count | rate_within_expected |
|---|---|---|---|---|---|
| B2 | ABSTAIN | ABSTAIN | CORRECT_SAFE_DEFERRAL | 12 | 1.0 |
| B2 | ANSWER | ABSTAIN | OVER_REFUSAL | 2 | 0.008333333333333333 |
| B2 | ANSWER | ANSWER | OTHER | 235 | 0.9791666666666666 |
| B2 | ANSWER | CLARIFY | OVER_REFUSAL | 3 | 0.0125 |
| B2 | CLARIFY | ABSTAIN | WRONG_DEFERRAL_TYPE | 12 | 0.5 |
| B2 | CLARIFY | ANSWER | UNSAFE_ANSWER | 12 | 0.5 |
| B2 | REFRESH | ABSTAIN | WRONG_DEFERRAL_TYPE | 24 | 0.5 |
| B2 | REFRESH | REFRESH | CORRECT_SAFE_DEFERRAL | 12 | 0.25 |
| B2 | REFRESH | REFUSE | WRONG_DEFERRAL_TYPE | 12 | 0.25 |
| B2 | REFUSE | ABSTAIN | WRONG_DEFERRAL_TYPE | 12 | 0.5 |
| B2 | REFUSE | ANSWER | UNSAFE_ANSWER | 12 | 0.5 |
| B2 | RETRY | ANSWER | UNSAFE_ANSWER | 7 | 0.5833333333333334 |
| B2 | RETRY | RETRY | CORRECT_SAFE_DEFERRAL | 5 | 0.4166666666666667 |
| C1 | ABSTAIN | ABSTAIN | CORRECT_SAFE_DEFERRAL | 12 | 1.0 |
| C1 | ANSWER | ABSTAIN | OVER_REFUSAL | 20 | 0.08333333333333333 |
| C1 | ANSWER | ANSWER | OTHER | 217 | 0.9041666666666667 |
| C1 | ANSWER | CLARIFY | OVER_REFUSAL | 3 | 0.0125 |
| C1 | CLARIFY | ANSWER | UNSAFE_ANSWER | 11 | 0.4583333333333333 |
| C1 | CLARIFY | CLARIFY | CORRECT_SAFE_DEFERRAL | 13 | 0.5416666666666666 |
| C1 | REFRESH | ABSTAIN | WRONG_DEFERRAL_TYPE | 12 | 0.25 |
| C1 | REFRESH | CLARIFY | WRONG_DEFERRAL_TYPE | 1 | 0.020833333333333332 |
| C1 | REFRESH | REFRESH | CORRECT_SAFE_DEFERRAL | 35 | 0.7291666666666666 |
| C1 | REFUSE | ABSTAIN | WRONG_DEFERRAL_TYPE | 12 | 0.5 |
| C1 | REFUSE | ANSWER | UNSAFE_ANSWER | 12 | 0.5 |
| C1 | RETRY | RETRY | CORRECT_SAFE_DEFERRAL | 12 | 1.0 |

## Highest-volume C1 failure cells

| dimension | slice | error_type | count | rate |
|---|---|---|---|---|
| difficulty | hard | WRONG_DEFERRAL | 25 | 0.1488095238095238 |
| expected_behavior | ANSWER | SQL_EXECUTION_ERROR | 24 | 0.1 |
| source | independent_adversarial | UNSAFE_ANSWER | 23 | 0.4791666666666667 |
| difficulty | medium | UNSAFE_ANSWER | 23 | 0.14743589743589744 |
| expected_behavior | ANSWER | OVER_REFUSAL | 23 | 0.09583333333333334 |
| source | compositional_held_out | SQL_EXECUTION_ERROR | 20 | 0.20833333333333334 |
| difficulty | hard | SQL_EXECUTION_ERROR | 19 | 0.1130952380952381 |
| difficulty | medium | OVER_REFUSAL | 18 | 0.11538461538461539 |
| expected_behavior | ANSWER | WRONG_RESULT | 18 | 0.075 |
| source | compositional_held_out | WRONG_RESULT | 16 | 0.16666666666666666 |

## Highest-rate C1 failure cells

| dimension | slice | error_type | count | rate |
|---|---|---|---|---|
| semantic_family | cache_version_validation | WRONG_DEFERRAL | 12 | 1.0 |
| semantic_family | cross_tenant_refusal | WRONG_DEFERRAL | 12 | 1.0 |
| semantic_family | missing_scope_refusal | UNSAFE_ANSWER | 12 | 1.0 |
| semantic_family | ambiguous_metric_clarification | UNSAFE_ANSWER | 11 | 0.9166666666666666 |
| semantic_family | keyword_campaign_multihop | SQL_EXECUTION_ERROR | 11 | 0.9166666666666666 |
| semantic_family | rolling_window_peak | WRONG_RESULT | 10 | 0.8333333333333334 |
| semantic_family | governed_schema_alias | OVER_REFUSAL | 7 | 0.5833333333333334 |
| expected_behavior | REFUSE | UNSAFE_ANSWER | 12 | 0.5 |
| expected_behavior | REFUSE | WRONG_DEFERRAL | 12 | 0.5 |
| semantic_family | campaign_budget_join | OVER_REFUSAL | 6 | 0.5 |

Machine-readable outputs include 18 error transitions and root-cause cross-tabs. Cell labels describe associations in stored fields, not causal root causes.
