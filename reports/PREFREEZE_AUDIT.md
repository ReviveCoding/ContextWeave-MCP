# Pre-freeze audit (in progress)

As of the reboot recovery, DESIGN_FREEZE and E08 are not authorized by the project protocol. E06 corrected-v3 B2 and paired C1 outcomes must complete, followed by a valid E07 paired power analysis.

## Verified inputs

- The pilot is exactly 360 unique frozen task IDs. `benchmarks/pilot_programmatic.jsonl` hashes to `6cfa67f0abd89b954210d68e88f8cdbc9c1cd3bb961c65b899759c89dc21363f` and matches `benchmarks/pilot_manifest.json` and RUN_STATE.
- A read-only re-execution of all 360 corrected gold SQL tasks against the immutable v2 warehouse found zero result-hash mismatches (`evidence/pilot/frozen_gold_audit.json`).
- The immutable v2 warehouse SHA-256 is `d50277f36f4fc1b86ac196c327f3ccb450a18895325f78aea228f5f6d8d90ddf`.
- The C1 reranking file SHA-256 matches its qualification receipt: `eb9690c5b2221c70ed57a1661484499445fa39d0ce253d078e30f3f0e03d0bc7`.
- Qwen3-4B is pinned to revision `1cfa9a7208912126459214e8b04321603b3df60c`; the B2 restart has one CUDA owner at batch size 4.
- Invalid-gold and invalid alias-scoring outputs remain separate and excluded from corrected-v3 outcomes.

## Pending gates

- Complete B2 and C1 with the exact same 360 task identities, revisions, parser, SQL sandbox, and generation controls.
- Validate each checkpoint for completeness, uniqueness, CUDA execution, method identity, and frozen task hash.
- Compute paired success, discordance, task-family variance, and a defensible non-inferiority sample size. Preserve an `INSUFFICIENT_POWER` result if required N exceeds the predeclared feasible maximum of 600.
- Specify and freeze final task construction, group-disjoint splits, protected access rules, primary and secondary analyses, and the strongest eligible baseline before protected outcomes are seen.
- Keep the 40 independently authored adversarial tasks separate from the 360 programmatic pilot. They are compiled and unrun.

No protected benchmark, final method, or promotion decision exists yet.
