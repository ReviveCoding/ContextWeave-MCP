# T1 Criteo data audit

Canonical aggregate: `evidence/data/criteo_eda.json`. T1 is real public event structure, not incident or policy truth.

- n: 16468027
- min_ts: 0
- max_ts: 2671199
- users: 6142256
- campaigns: 675
- clicks: 5947563
- conversion_rows: 806196
- attributed_rows: 442424
- malformed_rows: 0
- domain_invalid_rows: 0
- duplicate_hash_rows: 0
- max_user_events: 880

Costs are transformed values, not real paid amounts. Conversion labels and attribution are future-looking; task construction must avoid temporal leakage.
Daily distributions, null counts, and campaign concentration are in the canonical JSON. The duplicate count is a hash-based proxy.
