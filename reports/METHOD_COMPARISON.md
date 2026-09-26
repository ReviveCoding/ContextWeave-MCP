# Method comparison

## Scope

Only B2 and C1 were executed on the complete v2 qualification set. The wider baseline ladder and protected comparison were gated by E07. The comparison below is evidence class Q and is not a confirmatory efficacy comparison.

| Method | Qualification success | Canonical outcome SHA-256 |
|---|---:|---|
| B2 BM25 Top-k | 200/360 (55.56%) | `e1dd2d277f14fa4136109c3df18e79d7241b450d6995c97f21a2d0a45a07ba3f` |
| C1 ContextWeave-R | 247/360 (68.61%) | `a45de1cd48c8a8b9d6bc7607cf1c71328067d66dca3700ef95e8c0da2abfeb33` |

The paired cells were 75 candidate-only successes and 28 baseline-only successes, giving an observed +13.06 percentage-point paired difference. Equal family weighting gives the same point estimate because every family contains 12 tasks. This positive qualification result may be used for design planning and failure analysis only.

## Power gate

The original v2 E07 simulation is preserved as `SUPERSEDED_INVALID_CALIBRATION`. Clipping and pseudocount shrinkage moved its intended null mean from -0.05 to a positive value. The corrected identity, `ContextWeave-v2-E07-calibrated-family-t-v2`, restored the requested means and passed nominal normal-reference and homogeneous binary calibration checks. The observed-profile heterogeneous check was conservative.

The corrected analytic calculation required 799 independent families for target power 0.90. Across 46 simulated designs with 24–36 families, 10–20 tasks per family, and no more than 600 tasks, the greatest estimated power was 0.1165. V2 therefore closed as `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`.

## Unexecuted comparisons

B-2, B-1, B0, B1, B3–B7, C2, compression variants, token frontiers, ablations, and a locked final comparison are `NOT RUN / GATED`. No method was selected for production or protected evaluation. No task-token or task-latency superiority claim is supported.
