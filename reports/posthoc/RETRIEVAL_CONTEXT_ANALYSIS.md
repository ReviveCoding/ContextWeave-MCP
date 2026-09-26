# Retrieval and context analysis

> **This is post-release exploratory diagnostic analysis over qualification outcomes. It does not reopen the closed v2 scientific program, does not establish efficacy, and does not alter V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED.**

Analysis identity: ContextWeave-v2-posthoc-diagnostics-v1. Parent: contextweave-v2-release-closed-2026-09-25 at 3d0d44081e3a5a6f67b58846bfcd307e448658d8.

Coverage compares required IDs with stored top-20 rankings. Association does not prove causation. Rank shifts are unavailable.

| dimension | value | n | b2_success_rate | c1_success_rate | c1_only | b2_only |
|---|---|---|---|---|---|---|
| retrieval_complete_at_candidate_k | False | 302 | 0.543046357615894 | 0.6688741721854304 | 65 | 27 |
| retrieval_complete_at_candidate_k | True | 58 | 0.6206896551724138 | 0.7758620689655172 | 10 | 1 |
| retrieval_coverage_bin | complete | 58 | 0.6206896551724138 | 0.7758620689655172 | 10 | 1 |
| retrieval_coverage_bin | majority | 170 | 0.7235294117647059 | 0.6941176470588235 | 22 | 27 |
| retrieval_coverage_bin | none | 45 | 0.26666666666666666 | 0.7333333333333333 | 21 | 0 |
| retrieval_coverage_bin | partial | 87 | 0.3333333333333333 | 0.5862068965517241 | 22 | 0 |
| retrieval_first_required_rank_bin | missing | 45 | 0.26666666666666666 | 0.7333333333333333 | 21 | 0 |
| retrieval_first_required_rank_bin | rank_1 | 150 | 0.7 | 0.8133333333333334 | 35 | 18 |
| retrieval_first_required_rank_bin | rank_11_20 | 18 | 0.6666666666666666 | 0.7777777777777778 | 2 | 0 |
| retrieval_first_required_rank_bin | rank_2_5 | 131 | 0.5267175572519084 | 0.5648854961832062 | 15 | 10 |
| retrieval_first_required_rank_bin | rank_6_10 | 16 | 0.125 | 0.25 | 2 | 0 |
| c1_context_quartile | Q1 | 94 | 0.5 | 0.6808510638297872 | 24 | 7 |
| c1_context_quartile | Q2 | 90 | 0.4888888888888889 | 0.6222222222222222 | 14 | 2 |
| c1_context_quartile | Q3 | 86 | 0.7790697674418605 | 0.7441860465116279 | 11 | 14 |
| c1_context_quartile | Q4 | 90 | 0.4666666666666667 | 0.7 | 26 | 5 |
| c1_context_saturated | False | 360 | 0.5555555555555556 | 0.6861111111111111 | 75 | 28 |

## Missingness

{
  "per_task_latency": "unavailable; stored latency is batch-level",
  "selected_context_identities": "unavailable",
  "reranker_pre_rank": "unavailable; rank shifts cannot be computed",
  "dependency_depth": "no separate field; graph_distance and join_depth retained"
}

## Compute timing scope

90 stored four-task batch observations per method; not per-task or production latency. Stored batch percentiles:

```json
{
  "B2": {
    "batch_count": 90,
    "p50": 10.055567536990566,
    "p90": 17.999195026092643,
    "p95": 20.70738810425573,
    "p99": 25.246466398046312
  },
  "C1": {
    "batch_count": 90,
    "p50": 9.436697169000013,
    "p90": 15.981004920699935,
    "p95": 16.751855295299986,
    "p99": 19.494611808920073
  }
}
```

These qualification batch timings cannot be interpreted as per-task or production latency.
