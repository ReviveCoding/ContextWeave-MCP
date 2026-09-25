# ContextWeave v2 pre-protected protocol

Status: **closed before freeze as `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`**

Protocol identity: `ContextWeave-v2-family-diverse-qualification`

V1 remains closed and immutable as `V1_PRE_FREEZE_INSUFFICIENT_POWER`. V2 does not relabel v1 outcomes or reuse them as v2 observations.

## Scientific rationale

The v1 pilot had 360 tasks but only six independent semantic families. Its E07 sensitivity analysis showed that repetitions within those families could not substitute for independent family diversity. Matched binary non-inferiority work likewise shows that the number of independent clusters is the main power driver and that increasing cluster size has limited returns ([Nam 2011, DOI 10.1016/j.csda.2011.04.020](https://doi.org/10.1016/j.csda.2011.04.020)). Simulation studies of binary outcomes with few clusters support cluster-level analyses with a t reference distribution and show that uncorrected individual-level methods can misstate type I error ([Thompson et al. 2022, DOI 10.1186/s12874-022-01699-2](https://doi.org/10.1186/s12874-022-01699-2); [Westgate and Braun 2011, DOI 10.1002/sim.4101](https://doi.org/10.1002/sim.4101)).

These papers concern clustered trials, while this benchmark compares two methods on the same tasks rather than randomizing treatments. V2 therefore borrows their variance and small-cluster lessons, not their treatment-randomization interpretation. Randomization-based confidence intervals are retained as background but are not the primary analysis because method assignment is fixed ([Rabideau and Wang 2021, DOI 10.1093/biostatistics/kxaa007](https://doi.org/10.1093/biostatistics/kxaa007)).

## Qualification benchmark design

- Construct 30 independent semantic families with 12 paired tasks per family (360 tasks).
- Treat semantic family as the independent planning cluster and task as the paired observation.
- Use group-disjoint semantic family IDs and template signatures. No v1 family ID or normalized v1 template may be reused.
- Reserve protected construction for new family IDs and new templates after v2 E07. Protected tasks do not exist yet.
- Keep public, controlled synthetic, qualification, protected, and external evidence classes separate.
- Include programmatic known-answer, compositional, independently authored adversarial, and security/OOD sources.
- Validate executable SQL by normalized result-set equivalence. Score non-SQL tasks against explicit `CLARIFY`, `REFRESH`, `REFUSE`, `RETRY`, or `ABSTAIN` contracts.
- Keep Qwen3-4B revision, tokenizer, chat template, decoding, 1024-token context budget, CUDA backend, and batch size 4 fixed between paired B2 and C1 runs.

The family set spans lookup variants, multi-table joins, temporal aggregation/comparison, ratio and nested metrics, schema aliases, metric-version changes, policy grounding, ambiguity, freshness, authorization, schema drift, distractor stress, multi-hop dependencies, document-plus-SQL tasks, cache-sensitive tasks, retry and safe abstention.

## V2 E07 planning analysis

The absolute non-inferiority margin remains **0.05**. It has not been changed for feasibility. One-sided alpha remains 0.025 and target power remains 0.90. The feasible protected ceiling remains 600 tasks, with 24–36 independent semantic families and 10–20 tasks per family.

For task \(i\) in family \(j\), define paired difference \(D_{ij}=C1_{ij}-B2_{ij}\), where each success indicator is binary. The primary planning estimand is the equally family-weighted mean

\[
\bar D_F=K^{-1}\sum_{j=1}^{K}\bar D_j.
\]

Equal family weights ensure repeated instances in one family cannot dominate the scientific conclusion. The analytic sensitivity calculation uses the sample standard deviation of family means and a one-sample noncentral t calculation with \(K-1\) degrees of freedom. It reports both required family count and implied task count over the prespecified 10–20 task range. Task-level paired discordance is reported as a separate diagnostic.

Simulation-based power is mandatory. It will:

1. estimate each pilot family's four paired outcome probabilities (both correct, C1-only, B2-only, neither) with prespecified shrinkage;
2. resample or generate independent family effects, then generate 10–20 paired tasks within each family;
3. apply the exact planned family-level one-sided t test of \(H_0:\mu_F\le-0.05\);
4. evaluate 24–36 families and total N up to 600 with at least 10,000 deterministic replicates;
5. report between-family heterogeneity and sensitivity scenarios that inflate heterogeneity and set the planning mean difference to 0 as a conservative scientifically meaningful alternative;
6. require estimated power at least 0.90 and simulated type I error at most 0.025 plus Monte Carlo tolerance before any freeze.

The observed positive pilot difference may be reported but cannot be the only planning alternative. The zero-difference scenario asks whether C1 can be shown non-inferior when its true quality equals B2. This avoids selecting a favorable effect merely to make the design feasible.

## Small-cluster final inference assumptions

If v2 becomes design-ready, the frozen primary quality analysis will use family mean paired differences, equal family weights, a one-sided t critical value with \(K-1\) degrees of freedom, and the frozen 0.05 margin. A family bootstrap confidence interval and task-level McNemar result are supporting analyses. Family bootstrap resamples whole families and never individual tasks across family boundaries. Results will state that semantic families are designed benchmark clusters rather than a probability sample of every possible analytics task.

## Mechanical gate

V2 may create `DESIGN_FREEZE` and then `BENCHMARK_FREEZE` only if paired B2/C1 qualification outcomes are complete on identical task identities and both analytic and simulation-based clustered planning are defensible within 600 protected tasks. Otherwise close v2 as `INSUFFICIENT_POWER` and proceed to documentation/release without E08–E24 scientific claims.

## E07 calibration audit and closure

The first v2 E07 simulation is preserved as `SUPERSEDED_INVALID_CALIBRATION`. Its per-family clipping step did not preserve the requested null-boundary mean. A requested difference of -0.05 became +0.0652778 after clipping. The four-cell Dirichlet pseudocounts then implied +0.0580247, and an independent 100,000-replicate reproduction realized +0.0579013 with rejection probability 0.32821. This explains the anomalous reported Type I error; it was a generator error rather than evidence that the specified family t test rejects 32.8% at the true null boundary.

The corrected statistical identity is `ContextWeave-v2-E07-calibrated-family-t-v2`. It uses a bounded root solve after clipping, validates every four-cell probability vector, and makes the mean family difference equal the requested planning value to numerical precision. It then resamples whole family profiles and generates paired multinomial outcomes without the mean-shifting pseudocount draw.

For family differences \(D_j\), the prespecified test is

\[
H_0:\mu_D\le -0.05,\qquad H_1:\mu_D>-0.05,
\]

with statistic \(\sqrt{K}(\bar D+0.05)/s_D\), rejection above \(t_{0.975,K-1}\), equal family weights, standard error \(s_D/\sqrt K\), and \(K-1\) degrees of freedom. The sign and rejection direction are therefore correct.

Independent 100,000-replicate checks gave null rejection 0.02552 for an exact normal t benchmark and 0.02582 for homogeneous paired binary families. Both lie in the prespecified Monte Carlo compatibility interval [0.0215323, 0.0284677]. The observed-profile heterogeneous stress scenario realized mean -0.0495774 and rejection 0.01874. It is conservative and outside the narrow nominal-compatibility band, but it remains below the upper safety limit. The corrected design reports this distinction instead of calling the heterogeneous result exactly nominal.

The independent analytic calculation and project implementation both require 799 independent families for 0.90 power at true difference zero using the observed family standard deviation 0.4353200. Across 46 feasible designs with 24–36 families, 10–20 tasks per family, and at most 600 tasks, the largest simulated power was 0.1165; under 1.5x heterogeneity it was 0.0952. All 46 null-boundary simulations controlled Type I error under the prespecified safety limit, and no design met the power gate.

V2 is therefore closed as `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`. This is a benchmark design and power limitation. B2's 200/360 and C1's 247/360 outcomes, including the +0.1305556 paired qualification difference, remain qualification evidence only and do not establish efficacy, benefit, harm, or failure. No protected task was constructed or accessed, and no design or benchmark freeze exists.
