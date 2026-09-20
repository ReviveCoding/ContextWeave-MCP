# T1 conversion identity supplement

The canonical [supplement](../evidence/data/criteo_conversion_identity_supplement.json) separates event-row flags from distinct conversion IDs. The E03 audit counted 806,196 rows with `conversion=1`; 435,810 distinct non-sentinel conversion IDs occur on those rows, and 236,331 distinct IDs occur on rows with `attribution=1`. No conversion row had the sentinel ID `-1`.

The official source page describes approximately 45,000 conversions, which does not match these counts in the validated Criteo-owned mirror. The discrepancy is preserved. It may reflect a different definition or source-page summary; no unverified explanation is used as evidence. Downstream tasks must state whether they count impression rows, distinct conversion IDs, or attributed conversion rows. None of these labels establishes causal incident truth.
