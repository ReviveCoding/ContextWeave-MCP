# ContextWeave-MCP final technical report

## 1. Executive summary

ContextWeave-MCP reached a scientifically valid pre-freeze stopping point. V1 closed as `V1_PRE_FREEZE_INSUFFICIENT_POWER`. V2 broadened the qualification benchmark to 30 semantic families, but its original E07 simulation was invalidly calibrated and is preserved as `SUPERSEDED_INVALID_CALIBRATION`. After correction and independent calibration, the feasible design still lacked power. V2 closed as `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`.

## 2. Problem and industry context

The project investigates governed context selection for analytical agents over structured enterprise-style data. The intended tradeoff joins task quality, context cost, latency, freshness, dependencies, and authorization, with security constraints treated as hard gates.

## 3. Desktop study and related work

The desktop study pinned MCP 2.2.0 and protocol 2026-07-28, the public Criteo attribution dataset, Spider2-DBT, OpenRTB documentation, Qwen3-4B, BGE-M3, BGE-reranker-v2-m3, DuckDB, PyTorch, Transformers, and statistical tooling. See `reports/DESKTOP_STUDY.md` and `sources/registry.json`.

## 4. Research question and hypothesis

The planned primary question asked whether a dependency-aware context controller could be non-inferior in TaskSuccess while reducing context. The confirmatory hypothesis was never tested because power qualification failed before a protected benchmark or final method freeze existed.

## 5. Evidence domains and claim boundary

Real public events, controlled synthetic enterprise data, qualification outcomes, protected evidence, and external evidence remain separate. No evidence supports Amazon-internal use, production advertiser benefit, production security certification, production latency, distributed performance, or external task transfer.

## 6. Public data and provenance

T1 used the Criteo-owned attribution dataset mirror: 653,015,824 compressed bytes, SHA-256 `94ac7a465564349bc7ba008602211d5990a3c53cc133abc0aadef61ea2391a98`, licensed CC BY-NC-SA 4.0 under recorded Criteo terms. Raw row-level data is excluded from Git.

## 7. EDA

The canonical audit covers 16,468,027 rows, 6,142,256 users, 675 campaigns, 5,947,563 click rows, 806,196 conversion-flag rows, 442,424 attributed rows, and 31 indexed days. It found zero malformed and domain-invalid rows under implemented checks. Cost values are transformed and do not represent paid amounts. See `reports/DATA_AUDIT.md` and its conversion-identity supplement.

## 8. Enterprise warehouse

The controlled T3 warehouse contains 36 tables and 425 columns. `campaign_daily` aggregates T1 structure; other enterprise tables and policies are explicitly controlled synthetic values. The immutable database identity is `d50277f36f4fc1b86ac196c327f3ccb450a18895325f78aea228f5f6d8d90ddf`.

## 9. Benchmark construction

V2 compiled 360 qualification tasks across 30 semantic families with 12 tasks per family, group-disjoint family identities, known-answer SQL or explicit governed behaviors, and an independently authored adversarial subset. Manifest SHA-256 is `38cc188a25252a4d7eb981f8a1d24b838aecc83686c24091ccba4c1e1a76ce99`.

## 10. Semantic catalog and graph

The catalog contains seven governed metrics. The audited dependency graph contains 14 nodes and 24 edges and passed deterministic critical-closure checks. This is implementation evidence, not a final retrieval result.

## 11. Baselines

Only B2 was completed on v2 qualification. The wider baseline ladder was gated before protected execution. B2 succeeded on 200/360 tasks.

## 12. ContextWeave-R

C1 ContextWeave-R completed the same 360 task identities with the same Qwen revision, CUDA/Transformers backend, bfloat16 dtype, batch size 4, context budget, decoding, and scoring rules. C1 succeeded on 247/360 tasks.

## 13. Utility intervention study

E13 was `NOT RUN / GATED`. No marginal-utility training or protected intervention result exists.

## 14. ContextWeave-L

E14 was `NOT RUN / GATED`. No learned candidate was promoted or compared.

## 15. Compression

E15 was `NOT RUN / GATED`. No compression approach passed a final qualification gate.

## 16. MCP, authorization, and security

The implemented MCP surface passed in-memory, stdio, and Streamable HTTP smoke checks. Unit tests cover representative JWT, SQL-sandbox, and cache-isolation behavior. E19 was `NOT RUN / GATED`, so no security hard-gate or certification claim is supported.

## 17. Experimental protocol

V2 retained absolute NI margin 0.05, one-sided alpha 0.025, target power 0.90, equal family weights, and a 600-task ceiling. The planned family statistic was \(\sqrt K(\bar D+0.05)/s_D\) compared with \(t_{0.975,K-1}\).

## 18. Retrieval results

V2 retrieval artifacts cover all 360 qualification identities with BGE-M3 revision `5617a9f61b028005a4858fdac845db406aefb181` and reranker revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`. This is pipeline qualification; E10 protected retrieval comparisons were not run.

## 19. Context efficiency

E16 and the protected context-token comparison were `NOT RUN / GATED`. No context-efficiency superiority claim is supported.

## 20. End-to-end agent results

E17 and E24 were `NOT RUN / GATED`. The qualification TaskSuccess difference cannot substitute for an end-to-end locked result.

## 21. Cache and freshness

Cache identity and isolation unit tests exist. E18 sequence experiments were `NOT RUN / GATED`; no hit-rate, stale-error, or latency frontier is claimed.

## 22. Security

E19 was `NOT RUN / GATED`. No zero-violation scientific result is imputed from the absence of a protected experiment.

## 23. OOD and stress

E20 was `NOT RUN / GATED`. No stress-world heatmap or robustness claim exists.

## 24. Systems and GPU

Local qualification used one RTX 4090 Laptop GPU. Codex itself was remote. The project did not execute E21 systems benchmarking, so no production latency, throughput, availability, energy, distributed, or multi-GPU claim is supported.

## 25. Ablations

E22 ablations were `NOT RUN / GATED`; no component causal contribution is claimed.

## 26. Error analysis

Infrastructure interruption receipts, invalid-gold pilots, alias-scoring outputs, partial checkpoints, and the invalid E07 simulation are preserved separately. E25 protected post-audit slicing was `NOT RUN / GATED`.

## 27. External validation

Spider2-DBT source metadata was pinned, but E23 execution was `NOT RUN / GATED`. No external-transfer claim is supported.

## 28. Final scientific decision

The v2 pilot observed 75 candidate-only and 28 baseline-only successes, a +13.06 percentage-point paired difference. This is qualification evidence only and is not an efficacy claim. The corrected analytic design required 799 families; maximum feasible simulated power was 0.1165. The mechanical decision is `V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED`.

## 29. Limitations

Semantic families are designed clusters rather than a probability sample of all analytical tasks. Only qualification methods were run. No protected tasks, freezes, final context/token comparison, security experiment, systems benchmark, or external evaluation exists.

## 30. Future work

Any future scientific program must start under a new protocol identity and independently justify a feasible source of substantially more semantic-family information before protected access. V2 method selection remains closed.

## 31. Reproducibility

`reports/REPRODUCTION_GUIDE.md` defines the native WSL locked environment and the release-only quality command. Canonical evidence hashes are checked before generating figures or closing release state.

## 32. Claim ledger

`reports/CLAIM_LEDGER.md` is normative. The repository supports a local, public-data-anchored, controlled, single-GPU qualification record and a calibrated insufficient-power conclusion. It supports no efficacy, production, Amazon-internal, security-certification, or external-transfer claim.
