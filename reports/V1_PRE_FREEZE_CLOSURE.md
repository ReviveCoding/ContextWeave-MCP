# ContextWeave v1 pre-freeze closure

## Mechanical disposition

Protocol v1 is closed as **`V1_PRE_FREEZE_INSUFFICIENT_POWER`**.

This disposition records a benchmark-design and power limitation. It is not evidence that ContextWeave succeeded or failed. No protected outcome was accessed, and neither a `DESIGN_FREEZE` nor a `BENCHMARK_FREEZE` was created. E08 is illegal under v1.

## Audited qualification evidence

- Corrected-v3 task manifest: 360 unique tasks, SHA-256 `6cfa67f0abd89b954210d68e88f8cdbc9c1cd3bb961c65b899759c89dc21363f`.
- B2: 360/360 task identities in manifest order, 266 correct, CUDA Qwen3-4B revision `1cfa9a7208912126459214e8b04321603b3df60c`, batch size 4, outcome SHA-256 `018cf7054702491e3608bdeb3835631be72a23572967e761dfb5538915891f69`.
- C1: 360/360 task identities in manifest order, 308 correct, the same model revision/device/batch/task identities, outcome SHA-256 `e0efc98064fd83d7d4aacbe952f2994b81894f2752ed0d0cba0bda8a5f937f1f`.
- E07: 59 candidate-only successes, 17 baseline-only successes, paired difference 0.1166667, discordance 0.2111111, task-paired required N 75, six-family sensitivity required N 3165, feasible ceiling 600, status `INSUFFICIENT_POWER`.
- Receipt-output audit: 27 outputs checked with no unexplained mismatches. Two historical mutable E00 outputs remain explicitly identified as caveats.
- The interrupted and GPU-guard receipts remain preserved. Invalid-gold and alias-sensitive pilot outputs remain separately labeled in `evidence/pilot/superseded_manifest.json` and were not counted.
- The E06 supervisor and model process were no longer alive at the closure audit; `nvidia-smi` reported no compute process. The stale supervisor log records an earlier interrupted wait and is not scientific evidence.

## Exact six-family sensitivity derivation

For paired task outcome difference \(D_i=C1_i-B2_i\), E07 observed:

- \(n=360\), candidate-only = 59, baseline-only = 17;
- \(\hat\delta=(59-17)/360=0.1166667\);
- discordance \(=(59+17)/360=0.2111111\);
- task variance proxy \(0.2111111-0.1166667^2=0.1975\);
- family mean differences: 0, 0, 0.8666667, 0, -0.1666667, 0;
- sample variance of the six family means: 0.1394444;
- the implemented family sensitivity variance proxy: \(0.1394444\times(360/6)=8.3666667\).

With one-sided alpha 0.025, target power 0.90, and the unchanged absolute NI margin 0.05:

\[
(z_{0.975}+z_{0.90})^2=10.5074231,
\quad (\hat\delta+0.05)^2=0.0277778.
\]

The implementation therefore gives:

- task-paired estimate: \(\lceil10.5074231\times0.1975/0.0277778\rceil=75\);
- family sensitivity: \(\lceil10.5074231\times8.3666667/0.0277778\rceil=3165\).

The 3165 value is a conservative planning diagnostic. It comes from only six equally sized, highly repetitive semantic families. Its conversion of family-mean variance to a per-task variance assumes added information arrives through new independent families while retaining the observed 60 tasks per family. It does not directly model unequal family sizes, paired binary covariance within families, uncertainty in the heterogeneity estimate, or small-cluster degrees of freedom. It is not a confirmatory efficacy estimate and cannot be used to claim benefit or harm.

## Consequence for v2

V2 must obtain its primary information from many independent semantic families, estimate paired discordance and between-family heterogeneity on a new qualification pilot, and combine an analytic approximation with simulation under small-cluster-aware inference. V1 artifacts and identities remain immutable inputs to the audit trail, not v2 outcomes.
