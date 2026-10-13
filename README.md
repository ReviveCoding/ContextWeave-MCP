# ContextWeave-MCP

[![CI](https://github.com/ReviveCoding/ContextWeave-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/ReviveCoding/ContextWeave-MCP/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/ReviveCoding/ContextWeave-MCP?label=release)](https://github.com/ReviveCoding/ContextWeave-MCP/releases)

ContextWeave-MCP evaluates how a tool-using analytical agent selects enough context to answer a question without relying only on semantic similarity. The system retrieves candidate evidence, resolves metric and schema dependencies, enforces freshness and authorization rules, and packs context within a fixed token budget.

This is a local research implementation over public events and controlled synthetic enterprise metadata, not an integration with a production advertising system.

## The problem

A relevant document is not always sufficient context. Analytical questions may require a metric definition, its upstream dependencies, the applicable policy version, a join path, or confirmation that the source is fresh and permitted.

The retrieval pipeline combines:

- BM25 retrieval and BGE-M3 semantic retrieval with neural reranking;
- deterministic metric-dependency closure and context packing;
- freshness, authorization, and tenant-scope constraints;
- eight read-only MCP tools for catalog, policy, freshness, and SQL workflows;
- Qwen3-4B qualification with saved task identities and evaluation receipts.

The qualification configuration used a 1,024-token context budget. [Architecture](figures/F01_system_architecture.svg) and [technical report](reports/FINAL_TECHNICAL_REPORT.md) document the implemented system.

## Data and evaluation

The controlled DuckDB warehouse contains 36 tables and 425 columns. It was built using 16,468,027 audited rows from the public Criteo Attribution Modeling for Bidding dataset, together with explicitly synthetic enterprise objects, metrics, policies, permissions, and freshness states. These records are not production advertiser data.

The v2 benchmark consists of 360 paired tasks grouped into 30 semantic families. It includes 240 executable gold-SQL tasks and 120 governed-behavior tasks (answer, clarify, refresh, refuse, retry, or abstain). Both evaluated methods used the same task IDs and pinned Qwen revision.

| Method | Successful tasks | TaskSuccess |
| --- | ---: | ---: |
| B2: BM25 top-k context | 200/360 | 55.56% |
| C1: governed context selection | 247/360 | 68.61% |
| Observed paired difference | +47 net wins | +13.06 percentage points |

**These are qualification results, not confirmatory evidence of improvement.** The observed difference was concentrated in governed-behavior tasks, with remaining regressions in some SQL, refusal, and nested-metric families.

[Baseline comparison](figures/posthoc/P03_family_success_comparison.svg) · [Failure analysis](reports/posthoc/ERROR_ANALYSIS.md) · [Retrieval analysis](reports/posthoc/RETRIEVAL_CONTEXT_ANALYSIS.md)

## Why the study stopped before final evaluation

The initial clustered power simulation had a null-generation error. After correcting and independently calibrating the simulator, the planned confirmatory test required 799 independent semantic families to reach 90% analytic power. The strongest feasible design under the 600-task ceiling reached only 11.65% simulated power.

No protected final benchmark was created or accessed, and the planned context-efficiency superiority claim was not tested. The study closed as V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED.

The [claim ledger](reports/CLAIM_LEDGER.md), [power analysis](reports/E07_POWER_PLAN.md), and [final technical report](reports/FINAL_TECHNICAL_REPORT.md) retain the negative result and its limitations.

## MCP and software checks

Eight read-only MCP tools cover schema search, metric definitions, policy lookup, freshness, time-series queries, SQL explanation, and sandboxed queries. Smoke tests exercised in-memory, stdio, and Streamable HTTP paths. These checks do not establish production availability or security certification.

The CPU quality suite uses Python 3.12 and locked dependencies:

    git clone https://github.com/ReviveCoding/ContextWeave-MCP.git
    cd ContextWeave-MCP
    uv sync --locked --no-extra gpu --group dev
    uv run ruff format --check src tests scripts
    uv run ruff check src tests scripts
    uv run mypy --strict src/contextweave
    uv run python -m pytest -q
    uv run python scripts/audit_receipts.py --check-only
    uv run python scripts/validate_release.py
    uv run python scripts/validate_posthoc_v1.py

CI validates software and stored evidence; it does not redownload models or rerun the scientific qualification. GPU setup and pinned model revisions are documented in the [reproduction guide](reports/REPRODUCTION_GUIDE.md).

## Source and report map

| Path | Contents |
| --- | --- |
| src/contextweave/ | Retrieval, context planning, MCP interface, governance, and evaluation |
| tests/ | Software and recovery tests |
| benchmarks/ | Qualification task definitions |
| evidence/ | Results, receipts, and source hashes |
| warehouse/ | Controlled schema, metric catalog, and dependency graph |
| reports/ | Methods, statistical checks, failure analysis, and limitations |
| scripts/ | Reproducibility and validation commands |

Start with the [executive summary](reports/EXECUTIVE_SUMMARY.md) or [final technical report](reports/FINAL_TECHNICAL_REPORT.md). Post-hoc diagnostics are documented separately in [the analysis report](reports/posthoc/POSTHOC_DIAGNOSTIC_REPORT.md).

## Limitations and attribution

- Designed semantic families are not a representative sample of enterprise analytical workloads.
- Systems, cache, security, OOD, and external-transfer confirmation experiments were gated and not run.
- Timing recorded during qualification is not production latency.
- No confirmatory effect estimate, production benefit, or independent external transfer is established.

Author: Jinwoo Bae. Citation metadata is provided in [CITATION.cff](CITATION.cff).

This repository currently has no software license. Public access does not grant permission to copy, modify, or redistribute it beyond applicable law.
