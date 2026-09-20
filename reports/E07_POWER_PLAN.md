# E07 paired power plan (pilot qualification)

This plan was committed before corrected-v3 C1 outcomes were complete and before any protected benchmark existed. It does not claim a locked hypothesis result.

- **Paired unit:** task. Corrected-v3 B2 and C1 must each contain exactly the same 360 unique frozen task IDs, CUDA backend, Qwen3-4B revision, and task-manifest hash.
- **Planned primary comparison:** the selected ContextWeave method against the strongest eligible frozen baseline. B2/C1 pilot discordance is a planning proxy; it does not select the final baseline.
- **Quality criterion:** non-inferiority margin of 0.05 absolute TaskSuccess, one-sided alpha 0.025, target power 0.90.
- **Efficiency criterion:** material context reduction fraction of 0.20. The final hypothesis is conjunctive.
- **Sample-size estimate:** normal paired variance from discordant tasks; separately estimate semantic-family variation using the six pilot families. Use the larger required N and a fixed feasible ceiling of 600 locked tasks. If the NI planning effect is nonpositive or N exceeds 600, record `INSUFFICIENT_POWER`; do not relax the margin after protected access.
- **Family sensitivity assumption:** the family estimate treats new held-out semantic families, rather than more repetitions of the same six templates, as the source of added independent information. It is an approximate sensitivity check with only six observed families; it cannot establish confirmatory power on its own. Small-cluster sample-size methods may need simulation before any design freeze ([Hemming et al., *International Journal of Epidemiology*](https://pmc.ncbi.nlm.nih.gov/articles/PMC4521133/)).
- **Uncertainty plan:** 10,000 bootstrap replicates with seed 20260920. Assess semantic-family dependence before design freeze. Treat latency process/server replicate as an outer unit and use Holm adjustment for limited secondary method comparisons.
- **Protected access:** no protected outcomes have been accessed. Final test construction, eligible baseline, and analysis configuration must be frozen before one-shot evaluation.

The executable values and formula are in `src/contextweave/power.py`. `evidence/power/paired_design.json` and its receipt will be written only after both full pilot methods validate.
