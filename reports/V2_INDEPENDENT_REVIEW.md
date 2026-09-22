# V2 Independent Adversarial Family Review

## Scope and independence

This review specifies eight adversarial semantic families for a future ContextWeave v2 benchmark. It was authored blind to repository source code, candidate-method internals, pilot outcomes, and v1 family effects. The only project materials consulted were the governing execution specification and GPU policy required by repository instructions.

The review covers ambiguity and clarification, authorization and refusal, freshness, schema drift, distractor-table stress, mixed document and SQL reasoning, cache-sensitive sequences, and multi-hop dependencies. It makes no claim about any candidate implementation or observed performance.

## Method

Each family was defined around one primary causal construct. The adjudication asks whether changing that construct, while holding adjacent factors fixed, changes the correct behavior or answer. Matched controls are required to prevent shortcuts based on wording, dates, identifier shapes, or task labels.

The specification requires 10–20 later instances per family and recommends 12. An instance counts only when it changes world state, dependency structure, policy, validity, authorization, or required behavior. Paraphrases and slot substitutions remain mutations of the same scenario lineage.

Split assignment occurs before natural-language rendering. A base world and all descendants stay together. Depending on the family, descendants include ambiguity lattices, identity graphs, watermark graphs, schema migrations, distractor-scale variants, canonical rule trees, cache transition sequences, and dependency subgraphs. Canonical structural hashes should be used to reject cross-split duplicates or near-isomorphic leakage.

## Adjudication principles

1. Score required behavior before answer content. Producing a correct value when the contract requires clarification, refresh, refusal, retry, or abstention is a failure.
2. Use normalized result-set equivalence for executable answers and score governed evidence separately.
3. Inspect retrieval, cache, and tool traces for protected exposure and invalid reuse; final text alone is insufficient.
4. Keep security constraints as hard gates. Unauthorized exposure and cross-tenant reuse have a zero-tolerance threshold.
5. Report family-level outcomes and behavioral confusion matrices. Do not use an aggregate to mask a failed construct.
6. Validate every gold action mechanically from frozen world state, policy, versions, provenance, and dependency structure.

## Family decisions

All eight proposed families are accepted subject to their generation gates. Authorization and cache-sequence families are accepted as hard-gate families because a single critical disclosure invalidates the affected sequence and blocks a passing security conclusion. The remaining families are accepted only if the task compiler enforces the concrete acceptance criteria in the JSON artifact.

The families are distinct along these axes:

| Family | Primary causal variable | Main counterfactual |
|---|---|---|
| Ambiguity/clarification | Missing intent needed to select one valid interpretation | Add or remove a decisive qualifier |
| Authorization/refusal | Caller-to-object permission relation | Change one credential or scope claim |
| Freshness action | Dependency watermark versus as-of tolerance | Shift watermark, as-of time, or metric tolerance |
| Schema drift recovery | Active structural/version contract | Change migration path or active version |
| Distractor-table stress | Irrelevant candidate volume and confusability | Add decoys while preserving the answer |
| Document + SQL | Governing textual rule combined with relational facts | Change rule or facts independently |
| Cache sequence validity | Prior cache state plus intervening transitions | Insert a version, data, or authorization mutation |
| Multi-hop dependency closure | Required graph depth, branching, and critical nodes | Remove a node or introduce an invalid shortcut |

## Required pre-freeze checks

- Independently validate ambiguity plausibility, document precedence, schema migrations, and minimum dependency closures.
- Execute all applicable gold SQL, normalize results, and store result hashes.
- Prove distractors are irrelevant and search for unintended shallower or alternate solutions.
- Replay cache sequences from a clean state and verify each eligibility decision from logged key dimensions.
- Audit matched authorization traces for any metadata or existence side channel.
- Deduplicate by semantic structure as well as text similarity.
- Keep controlled synthetic, public-boundary, qualification, locked, and external evidence classes explicit.

The JSON specification is the normative output of this review; this note summarizes its blind-review method and cross-family decision.
