"""Deterministic exploratory diagnostics over immutable v2 qualification data."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import subprocess
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
TAG = "contextweave-v2-release-closed-2026-09-25"
PARENT = "3d0d44081e3a5a6f67b58846bfcd307e448658d8"
IDENTITY = "ContextWeave-v2-posthoc-diagnostics-v1"
BOUNDARY = (
    "This is post-release exploratory diagnostic analysis over qualification outcomes. "
    "It does not reopen the closed v2 scientific program, does not establish efficacy, "
    "and does not alter V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED."
)
SEED = 2026092601
REPLICATES = 100_000
DATA = ROOT / "evidence/posthoc_v1"
REPORTS = ROOT / "reports/posthoc"
FIGURES = ROOT / "figures/posthoc"
SAFE = {"CLARIFY", "REFRESH", "REFUSE", "RETRY", "ABSTAIN"}
CORE = (
    "benchmarks/v2_pilot_tasks.jsonl",
    "evidence/pilot_v2/b2_qwen3_4b.jsonl",
    "evidence/pilot_v2/c1_qwen3_4b.jsonl",
    "evidence/pilot_v2/b2_summary.json",
    "evidence/pilot_v2/c1_summary.json",
    "evidence/power_v2/calibration_audit.json",
    "evidence/power_v2/clustered_design_calibrated.json",
    "reports/V2_PROTOCOL.md",
    "reports/CLAIM_LEDGER.md",
)
PREFIXES = ("evidence/retrieval_v2/", "evidence/catalog/", "evidence/warehouse/")
EXPECTED_SHA256 = {
    "benchmarks/v2_pilot_tasks.jsonl": "38cc188a25252a4d7eb981f8a1d24b838aecc83686c24091ccba4c1e1a76ce99",
    "evidence/pilot_v2/b2_qwen3_4b.jsonl": "e1dd2d277f14fa4136109c3df18e79d7241b450d6995c97f21a2d0a45a07ba3f",
    "evidence/pilot_v2/c1_qwen3_4b.jsonl": "a45de1cd48c8a8b9d6bc7607cf1c71328067d66dca3700ef95e8c0da2abfeb33",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify_release() -> dict[str, str]:
    resolved = subprocess.check_output(
        ["git", "rev-list", "-n", "1", TAG], cwd=ROOT, text=True
    ).strip()
    if resolved != PARENT:
        raise RuntimeError(f"release tag moved: {resolved}")
    tracked = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", TAG], cwd=ROOT, text=True
    ).splitlines()
    paths = sorted(set(CORE) | {p for p in tracked if p.startswith(PREFIXES)})
    unchanged = (
        subprocess.run(
            ["git", "diff", "--quiet", TAG, "--", *paths], cwd=ROOT, check=False
        ).returncode
        == 0
    )
    if not unchanged:
        raise RuntimeError("canonical evidence differs from the parent release")
    result: dict[str, str] = {}
    for relative in paths:
        current = (ROOT / relative).read_bytes()
        release_bytes = subprocess.check_output(["git", "show", f"{TAG}:{relative}"], cwd=ROOT)
        result[relative] = sha(release_bytes)
        expected = EXPECTED_SHA256.get(relative)
        if expected is not None and (sha(current) != expected or result[relative] != expected):
            raise RuntimeError(f"canonical SHA-256 differs: {relative}")
    return result


def response(row: dict[str, Any]) -> str:
    return "ANSWER" if row.get("sql") else str(row.get("observed_behavior") or "UNKNOWN")


def error(row: dict[str, Any]) -> str:
    if row["status"] == "CORRECT":
        return "CORRECT"
    expected, observed = row["expected_behavior"], response(row)
    if expected in SAFE and observed == "ANSWER":
        return "UNSAFE_ANSWER"
    if expected == "ANSWER" and observed in SAFE:
        return "OVER_REFUSAL"
    if expected in SAFE and observed in SAFE and expected != observed:
        return "WRONG_DEFERRAL"
    status = str(row["status"])
    if status == "NO_SQL":
        return "NO_SQL"
    if "PARSE" in status:
        return "SQL_PARSE_ERROR"
    if status.startswith("EXECUTION_ERROR"):
        return "SQL_EXECUTION_ERROR"
    if status == "WRONG_RESULT":
        return "WRONG_RESULT"
    if status == "WRONG_BEHAVIOR":
        return "WRONG_BEHAVIOR"
    return "OTHER"


def quartiles(values: Sequence[int]) -> tuple[list[str], list[float]]:
    cuts = [float(x) for x in np.quantile(np.asarray(values), [0.25, 0.5, 0.75])]
    labels = [
        "Q1"
        if value <= cuts[0]
        else "Q2"
        if value <= cuts[1]
        else "Q3"
        if value <= cuts[2]
        else "Q4"
        for value in values
    ]
    return labels, cuts


def retrieval(task: dict[str, Any], ranking: list[str]) -> dict[str, Any]:
    required = [f"TABLE:{x}" for x in task["required_tables"]]
    required += [f"COLUMN:{x}" for x in task["required_columns"]]
    required += [f"METRIC:{x}" for x in task["required_metrics"]]
    required += [f"DOCUMENT:{x}" for x in task["required_docs"]]
    ranks = [ranking.index(token) + 1 for token in required if token in ranking]
    denominator = len(required)
    return {
        "retrieval_required_count": denominator,
        "retrieval_required_found": len(ranks),
        "retrieval_coverage": len(ranks) / denominator if denominator else None,
        "retrieval_first_required_rank": min(ranks) if ranks else None,
        "retrieval_recall_at_5": sum(x <= 5 for x in ranks) / denominator if denominator else None,
        "retrieval_recall_at_10": sum(x <= 10 for x in ranks) / denominator
        if denominator
        else None,
        "retrieval_recall_at_20": sum(x <= 20 for x in ranks) / denominator
        if denominator
        else None,
        "retrieval_candidate_k": len(ranking),
        "retrieval_complete_at_candidate_k": bool(required) and len(ranks) == denominator,
    }


def master_table() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = rows(ROOT / "benchmarks/v2_pilot_tasks.jsonl")
    b2_rows = rows(ROOT / "evidence/pilot_v2/b2_qwen3_4b.jsonl")
    c1_rows = rows(ROOT / "evidence/pilot_v2/c1_qwen3_4b.jsonl")
    b2 = {x["task_id"]: x for x in b2_rows}
    c1 = {x["task_id"]: x for x in c1_rows}
    ranks = {
        x["task_id"]: x["reranked"] for x in rows(ROOT / "evidence/retrieval_v2/rankings.jsonl")
    }
    ids = [x["task_id"] for x in tasks]
    if len(ids) != 360 or len(set(ids)) != 360 or set(ids) != set(b2) or set(ids) != set(c1):
        raise RuntimeError("paired task identities differ")
    families = Counter(x["semantic_family"] for x in tasks)
    if len(families) != 30 or set(families.values()) != {12}:
        raise RuntimeError("family structure differs")
    query_values = [len(x["query"].split()) for x in tasks]
    b2_context = [int(b2[x]["context_tokens"]) for x in ids]
    c1_context = [int(c1[x]["context_tokens"]) for x in ids]
    query_q, query_cuts = quartiles(query_values)
    b2_q, b2_cuts = quartiles(b2_context)
    c1_q, c1_cuts = quartiles(c1_context)
    output: list[dict[str, Any]] = []
    for index, task in enumerate(tasks):
        task_id = task["task_id"]
        base, candidate = b2[task_id], c1[task_id]
        b_ok, c_ok = base["status"] == "CORRECT", candidate["status"] == "CORRECT"
        transition = (
            "BOTH_CORRECT"
            if b_ok and c_ok
            else "C1_ONLY"
            if c_ok
            else "B2_ONLY"
            if b_ok
            else "BOTH_WRONG"
        )
        sql = task.get("gold_sql") or ""
        joins = len(re.findall(r"\bJOIN\b", sql, re.IGNORECASE))
        joined = " ".join(
            (task["family"], task["semantic_family"], str(task.get("scenario") or ""))
        ).lower()
        row: dict[str, Any] = {
            "task_id": task_id,
            "semantic_family": task["semantic_family"],
            "family": task["family"],
            "source": task["source"],
            "difficulty": task["difficulty"],
            "expected_behavior": task["expected_behavior"],
            "schema_version": task["schema_version"],
            "metric_version": task["metric_version"],
            "required_tables_count": task["required_table_count"],
            "required_columns_count": task["required_column_count"],
            "required_metrics_count": task["required_metric_count"],
            "required_docs_count": len(task["required_docs"]),
            "dependency_count": task["required_table_count"]
            + task["required_column_count"]
            + task["required_metric_count"]
            + len(task["required_docs"]),
            "graph_distance": task["graph_distance"],
            "join_depth": task["join_depth"],
            "query_character_length": len(task["query"]),
            "query_word_length": query_values[index],
            "query_length_quartile": query_q[index],
            "task_mode": "EXECUTABLE_SQL"
            if task["expected_behavior"] == "ANSWER"
            else "GOVERNED_BEHAVIOR",
            "independent_review_member": bool(task["independent_review_family"]),
            "gold_join_complexity": "zero_join"
            if joins == 0
            else "one_join"
            if joins == 1
            else "multi_join",
            "aggregation_or_window": bool(
                re.search(r"\b(SUM|COUNT|AVG|MIN|MAX|GROUP BY|OVER)\b", sql, re.IGNORECASE)
            ),
            "temporal_indicator": bool(task["temporal_operations"] or "temporal" in joined),
            "ratio_nested_metric_indicator": any(
                x in joined for x in ("ratio", "nested", "metric")
            ),
            "policy_document_indicator": bool(task["policy_dependencies"] or task["required_docs"]),
            "ambiguity_indicator": bool(task["ambiguity"] or "ambigu" in joined),
            "freshness_indicator": "fresh" in joined or task["expected_behavior"] == "REFRESH",
            "authorization_indicator": "author" in joined or "refus" in joined,
            "schema_drift_indicator": "schema" in joined or task["schema_version"] != "v1",
            "cache_retry_indicator": "cache" in joined or "retry" in joined,
            "b2_status": base["status"],
            "c1_status": candidate["status"],
            "b2_correct": b_ok,
            "c1_correct": c_ok,
            "paired_transition": transition,
            "b2_error_class": error(base),
            "c1_error_class": error(candidate),
            "b2_observed_behavior": response(base),
            "c1_observed_behavior": response(candidate),
            "b2_context_tokens": base["context_tokens"],
            "c1_context_tokens": candidate["context_tokens"],
            "b2_context_quartile": b2_q[index],
            "c1_context_quartile": c1_q[index],
            "context_budget_tokens": base["context_budget_tokens"],
            "b2_context_saturated": base["context_tokens"] >= 0.9 * base["context_budget_tokens"],
            "c1_context_saturated": candidate["context_tokens"]
            >= 0.9 * candidate["context_budget_tokens"],
            "b2_batch_latency_seconds": base["batch_latency_seconds"],
            "c1_batch_latency_seconds": candidate["batch_latency_seconds"],
            "per_task_latency_available": False,
            "selected_context_identities_available": False,
        }
        row.update(retrieval(task, ranks.get(task_id, [])))
        coverage = row["retrieval_coverage"]
        row["retrieval_coverage_bin"] = (
            "none"
            if coverage == 0
            else "partial"
            if coverage is not None and coverage < 0.5
            else "majority"
            if coverage is not None and coverage < 1
            else "complete"
        )
        first_rank = row["retrieval_first_required_rank"]
        row["retrieval_first_required_rank_bin"] = (
            "missing"
            if first_rank is None
            else "rank_1"
            if first_rank == 1
            else "rank_2_5"
            if first_rank <= 5
            else "rank_6_10"
            if first_rank <= 10
            else "rank_11_20"
        )
        output.append(row)
    cells = Counter(x["paired_transition"] for x in output)
    if sum(x["b2_correct"] for x in output) != 200 or sum(x["c1_correct"] for x in output) != 247:
        raise RuntimeError("success totals differ")
    if cells["C1_ONLY"] != 75 or cells["B2_ONLY"] != 28:
        raise RuntimeError("paired cells differ")
    for method, source in (("B2", b2_rows), ("C1", c1_rows)):
        if any(
            len({row["batch_latency_seconds"] for row in source[index : index + 4]}) != 1
            for index in range(0, 360, 4)
        ):
            raise RuntimeError(f"{method} batch latency fields are internally inconsistent")
    metadata = {
        "query_quartile_cuts": query_cuts,
        "b2_context_quartile_cuts": b2_cuts,
        "c1_context_quartile_cuts": c1_cuts,
        "missingness": {
            "per_task_latency": "unavailable; stored latency is batch-level",
            "selected_context_identities": "unavailable",
            "reranker_pre_rank": "unavailable; rank shifts cannot be computed",
            "dependency_depth": "no separate field; graph_distance and join_depth retained",
        },
        "batch_latency_seconds": {
            method: {
                "batch_count": len(values),
                "p50": float(np.quantile(values, 0.50)),
                "p90": float(np.quantile(values, 0.90)),
                "p95": float(np.quantile(values, 0.95)),
                "p99": float(np.quantile(values, 0.99)),
            }
            for method, source in (("B2", b2_rows), ("C1", c1_rows))
            for values in [
                [float(source[index]["batch_latency_seconds"]) for index in range(0, 360, 4)]
            ]
        },
        "latency_scope": "90 stored four-task batch observations per method; not per-task or production latency",
    }
    return output, metadata


def ratio(a: float, b: float) -> float | None:
    return a / b if b else None


def slice_row(dimension: str, value: str, group: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(group)
    b2 = sum(x["b2_correct"] for x in group)
    c1 = sum(x["c1_correct"] for x in group)
    cells = Counter(x["paired_transition"] for x in group)
    b_fail, c_fail = n - b2, n - c1
    return {
        "dimension": dimension,
        "value": value,
        "n": n,
        "flag": "SMALL_SLICE" if n < 20 else None,
        "b2_correct": b2,
        "c1_correct": c1,
        "b2_success_rate": b2 / n,
        "c1_success_rate": c1 / n,
        "absolute_delta_pp": 100 * (c1 - b2) / n,
        "relative_success_rate_change": ratio(c1 - b2, b2),
        "b2_failures": b_fail,
        "c1_failures": c_fail,
        "relative_failure_reduction": ratio(b_fail - c_fail, b_fail),
        "both_correct": cells["BOTH_CORRECT"],
        "c1_only": cells["C1_ONLY"],
        "b2_only": cells["B2_ONLY"],
        "both_wrong": cells["BOTH_WRONG"],
        "discordance_rate": (cells["C1_ONLY"] + cells["B2_ONLY"]) / n,
        "net_paired_wins": cells["C1_ONLY"] - cells["B2_ONLY"],
    }


def grouped(rows_: Sequence[dict[str, Any]], dimensions: Sequence[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for dimension in dimensions:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows_:
            groups[str(row[dimension])].append(row)
        result.extend(slice_row(dimension, key, value) for key, value in sorted(groups.items()))
    return result


def tests_with_fdr(slices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    major = {
        "family",
        "expected_behavior",
        "difficulty",
        "source",
        "task_mode",
        "independent_review_member",
    }
    tested: list[dict[str, Any]] = []
    for row in slices:
        discordant = row["c1_only"] + row["b2_only"]
        if row["dimension"] in major and row["n"] >= 20 and discordant >= 10:
            value = dict(row)
            value["mcnemar_exact_p"] = float(binomtest(row["c1_only"], discordant, 0.5).pvalue)
            tested.append(value)
    order = sorted(range(len(tested)), key=lambda i: tested[i]["mcnemar_exact_p"])
    running = 1.0
    q = [1.0] * len(tested)
    for rank, index in reversed(list(enumerate(order, 1))):
        running = min(running, tested[index]["mcnemar_exact_p"] * len(tested) / rank)
        q[index] = running
    for index, value in enumerate(q):
        tested[index]["bh_fdr_q"] = value
        tested[index]["interpretation"] = "POSTHOC_EXPLORATORY"
    return tested


def family_table(rows_: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows_:
        groups[row["semantic_family"]].append(row)
    result = [slice_row("semantic_family", key, value) for key, value in sorted(groups.items())]
    delta_order = sorted(result, key=lambda x: (-x["absolute_delta_pp"], x["value"]))
    fail_order = sorted(result, key=lambda x: (-x["c1_failures"], x["value"]))
    for row in result:
        row["delta_rank"] = delta_order.index(row) + 1
        row["c1_failure_rank"] = fail_order.index(row) + 1
        row["global_net_win_contribution"] = row["net_paired_wins"] / 47
    return result


def behavior_table(rows_: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for method in ("b2", "c1"):
        counts = Counter((x["expected_behavior"], x[f"{method}_observed_behavior"]) for x in rows_)
        totals = Counter(x["expected_behavior"] for x in rows_)
        for (expected, observed), count in sorted(counts.items()):
            diagnostic = "OTHER"
            if expected in SAFE and observed == "ANSWER":
                diagnostic = "UNSAFE_ANSWER"
            elif expected == "ANSWER" and observed in SAFE:
                diagnostic = "OVER_REFUSAL"
            elif expected in SAFE and observed == expected:
                diagnostic = "CORRECT_SAFE_DEFERRAL"
            elif expected in SAFE and observed in SAFE:
                diagnostic = "WRONG_DEFERRAL_TYPE"
            result.append(
                {
                    "method": method.upper(),
                    "expected": expected,
                    "observed": observed,
                    "diagnostic": diagnostic,
                    "count": count,
                    "rate_within_expected": count / totals[expected],
                }
            )
    return result


def error_tables(rows_: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result: list[dict[str, Any]] = []
    dimensions = ("semantic_family", "difficulty", "expected_behavior", "source")
    for method in ("b2", "c1"):
        for dimension in ("overall", *dimensions):
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            if dimension == "overall":
                groups["ALL"] = list(rows_)
            else:
                for row in rows_:
                    groups[str(row[dimension])].append(row)
            for key, group in sorted(groups.items()):
                for error_name, count in sorted(
                    Counter(x[f"{method}_error_class"] for x in group).items()
                ):
                    result.append(
                        {
                            "method": method.upper(),
                            "dimension": dimension,
                            "slice": key,
                            "error_type": error_name,
                            "count": count,
                            "rate": count / len(group),
                        }
                    )
    transitions = Counter((x["b2_error_class"], x["c1_error_class"]) for x in rows_)
    cross: dict[str, list[dict[str, Any]]] = {}
    dimensions2 = (
        "semantic_family",
        "expected_behavior",
        "difficulty",
        "source",
        "required_tables_count",
        "dependency_count",
        "gold_join_complexity",
        "query_length_quartile",
        "retrieval_complete_at_candidate_k",
        "retrieval_coverage_bin",
        "c1_context_quartile",
    )
    for dimension in dimensions2:
        counts = Counter((str(x[dimension]), x["paired_transition"]) for x in rows_)
        cross[dimension] = [
            {"slice": key[0], "transition": key[1], "count": count}
            for key, count in sorted(counts.items())
        ]
    detail = {
        "error_transitions": [
            {"b2_error": key[0], "c1_error": key[1], "count": count}
            for key, count in sorted(transitions.items())
        ],
        "root_cause_cross_tabs": cross,
        "highest_volume_failure_cells": sorted(
            (
                {
                    "dimension": row["dimension"],
                    "slice": row["slice"],
                    "error_type": row["error_type"],
                    "count": row["count"],
                    "rate": row["rate"],
                }
                for row in result
                if row["method"] == "C1"
                and row["dimension"] != "overall"
                and row["error_type"] != "CORRECT"
            ),
            key=lambda row: (-row["count"], -row["rate"], row["dimension"], row["slice"]),
        )[:20],
        "highest_rate_failure_cells": sorted(
            (
                {
                    "dimension": row["dimension"],
                    "slice": row["slice"],
                    "error_type": row["error_type"],
                    "count": row["count"],
                    "rate": row["rate"],
                }
                for row in result
                if row["method"] == "C1"
                and row["dimension"] != "overall"
                and row["error_type"] != "CORRECT"
                and row["count"] >= 3
            ),
            key=lambda row: (-row["rate"], -row["count"], row["dimension"], row["slice"]),
        )[:20],
    }
    return result, detail


def lofo(families: Sequence[dict[str, Any]]) -> dict[str, Any]:
    observed = 47 / 360
    output = []
    for family in families:
        n = 360 - family["n"]
        b2, c1 = 200 - family["b2_correct"], 247 - family["c1_correct"]
        delta = (c1 - b2) / n
        output.append(
            {
                "removed_family": family["value"],
                "b2_rate": b2 / n,
                "c1_rate": c1 / n,
                "paired_delta": delta,
                "delta_shift": delta - observed,
            }
        )
    values = [x["paired_delta"] for x in output]
    return {
        "identity": IDENTITY,
        "classification": "POSTHOC_EXPLORATORY",
        "baseline_delta": observed,
        "rows": output,
        "minimum_delta": min(values),
        "maximum_delta": max(values),
        "mean_delta": float(np.mean(values)),
        "median_delta": float(np.median(values)),
        "most_influential_positive_family": min(output, key=lambda x: x["delta_shift"])[
            "removed_family"
        ],
        "most_influential_negative_family": max(output, key=lambda x: x["delta_shift"])[
            "removed_family"
        ],
    }


def bootstrap(families: Sequence[dict[str, Any]]) -> dict[str, Any]:
    effects = np.asarray([x["net_paired_wins"] / x["n"] for x in families])
    rng = np.random.default_rng(SEED)
    samples = np.empty(REPLICATES)
    for start in range(0, REPLICATES, 10_000):
        size = min(10_000, REPLICATES - start)
        indices = rng.integers(0, len(effects), size=(size, len(effects)))
        samples[start : start + size] = effects[indices].mean(axis=1)
    counts, edges = np.histogram(samples, bins=60)
    return {
        "identity": IDENTITY,
        "classification": "POSTHOC_EXPLORATORY",
        "seed": SEED,
        "replicates": REPLICATES,
        "resampling_unit": "semantic_family; all 12 tasks preserved",
        "observed_delta": 47 / 360,
        "mean": round(float(samples.mean()), 15),
        "standard_deviation": round(float(samples.std(ddof=1)), 15),
        "percentile_interval_95": [float(x) for x in np.quantile(samples, [0.025, 0.975])],
        "probability_delta_gt_zero": float(np.mean(samples > 0)),
        "probability_delta_gt_negative_0_05": float(np.mean(samples > -0.05)),
        "histogram": {"counts": counts.tolist(), "edges": edges.tolist()},
        "warning": "POSTHOC EXPLORATORY; does not reverse the v2 power gate.",
    }


def concentration(families: Sequence[dict[str, Any]]) -> dict[str, Any]:
    def summarize(values: Sequence[int]) -> dict[str, Any]:
        ordered = sorted(values, reverse=True)
        total = sum(ordered)
        shares = [x / total for x in ordered] if total else [0.0] * len(ordered)
        return {
            "total": total,
            "top_shares": {
                str(k): sum(ordered[:k]) / total if total else None for k in (1, 3, 5, 10)
            },
            "herfindahl": sum(x * x for x in shares),
        }

    positive = [max(0, x["net_paired_wins"]) for x in families]
    ordered_positive = sorted(positive, reverse=True)
    return {
        "identity": IDENTITY,
        "classification": "POSTHOC_EXPLORATORY",
        "global_net_wins": 47,
        "positive_net_wins": {
            **summarize(positive),
            "top_shares_of_global_net_47": {
                str(k): sum(ordered_positive[:k]) / 47 for k in (1, 3, 5, 10)
            },
            "note": "Positive family contributions total 73; negative family contributions net this to 47.",
        },
        "c1_failures": summarize([x["c1_failures"] for x in families]),
    }


def backlog(rows_: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = {
        "SQL_EXECUTION_ERROR": (
            4,
            "sql_execution",
            "Audit identifiers and sandbox-compatible SQL.",
        ),
        "WRONG_RESULT": (4, "sql_generation", "Add targeted join and aggregation qualification."),
        "UNSAFE_ANSWER": (5, "behavior_control", "Gate executable output by expected behavior."),
        "WRONG_DEFERRAL": (3, "behavior_control", "Improve exact deferral routing."),
        "OVER_REFUSAL": (
            3,
            "behavior_control",
            "Improve answerability without weakening policy gates.",
        ),
        "NO_SQL": (3, "sql_generation", "Improve structured emission and parser recovery."),
        "WRONG_BEHAVIOR": (3, "behavior_control", "Strengthen behavior routing."),
    }
    output = []
    counts = Counter(x["c1_error_class"] for x in rows_ if not x["c1_correct"])
    for name, count in counts.items():
        severity, subsystem, mitigation = rules.get(
            name, (2, "other", "Inspect stored outputs and add targeted qualification.")
        )
        confidence = 1.0 if name in rules else 0.5
        output.append(
            {
                "issue": name,
                "evidence": "stored C1 status and behavior fields",
                "affected_slices": sorted(
                    {x["semantic_family"] for x in rows_ if x["c1_error_class"] == name}
                ),
                "affected_slice_count": len(
                    {x["semantic_family"] for x in rows_ if x["c1_error_class"] == name}
                ),
                "frequency": count,
                "severity": severity,
                "confidence": confidence,
                "likely_subsystem": subsystem,
                "proposed_mitigation": mitigation,
                "requires_new_scientific_protocol": True,
                "impact": count * severity * confidence,
                "causal_claim": False,
            }
        )
    incomplete = [
        x
        for x in rows_
        if x["retrieval_coverage"] is not None
        and x["retrieval_coverage"] < 1
        and not x["c1_correct"]
    ]
    if incomplete:
        output.append(
            {
                "issue": "RETRIEVAL_COVERAGE_ASSOCIATION",
                "evidence": "required IDs absent from stored top-20 on failed tasks",
                "affected_slices": sorted({x["semantic_family"] for x in incomplete}),
                "affected_slice_count": len({x["semantic_family"] for x in incomplete}),
                "frequency": len(incomplete),
                "severity": 3,
                "confidence": 0.5,
                "likely_subsystem": "retrieval",
                "proposed_mitigation": "Add exact dependency injection, then test in a new protocol.",
                "requires_new_scientific_protocol": True,
                "impact": len(incomplete) * 1.5,
                "causal_claim": False,
            }
        )
    return sorted(output, key=lambda x: (-x["impact"], x["issue"]))


def write_csv(path: Path, values: Sequence[dict[str, Any]]) -> None:
    fields = sorted(set().union(*(x.keys() for x in values)))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)
    temporary.replace(path)


def svg(
    title: str,
    labels: Sequence[str],
    series: Sequence[tuple[str, Sequence[float], str]],
    path: Path,
    maximum: float | None = None,
) -> None:
    top = maximum or max((max(x[1]) for x in series), default=1) or 1
    bottom = min((min(x[1]) for x in series), default=0)
    bottom = min(0.0, bottom)
    scale = 390 / (top - bottom)
    zero_y = 110 + top * scale
    width = 930 / max(len(labels), 1)
    content = []
    for index, label in enumerate(labels):
        origin = 190 + index * width
        for offset, (name, values, color) in enumerate(series):
            bar_width = width * 0.72 / len(series)
            height = abs(values[index]) * scale
            x = origin + offset * bar_width
            y = zero_y - height if values[index] >= 0 else zero_y
            content.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 2:.1f}" '
                f'height="{height:.1f}" fill="{color}"/>'
            )
        content.append(
            f'<text x="{origin:.1f}" y="525" class="l" text-anchor="end" '
            f'transform="rotate(-45 {origin:.1f} 525)">{html.escape(label[:25])}</text>'
        )
    for index, (name, _, color) in enumerate(series):
        content.append(
            f'<rect x="30" y="{100 + index * 23}" width="15" height="15" fill="{color}"/>'
            f'<text x="52" y="{113 + index * 23}" class="l">{html.escape(name)}</text>'
        )
    document = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="620">'
        "<style>.t{font:700 25px system-ui;fill:#0f172a}.s{font:15px system-ui;fill:#475569}"
        '.l{font:12px system-ui;fill:#1e293b}</style><rect width="1200" height="620" fill="#f8fafc"/>'
        f'<text x="30" y="40" class="t">{html.escape(title)}</text>'
        f'<text x="30" y="67" class="s">{html.escape(BOUNDARY)}</text>'
        + "".join(content)
        + '<text x="30" y="602" class="s">POSTHOC EXPLORATORY — qualification only.</text></svg>\n'
    )
    write_text(path, document)


def heatmap_svg(families: Sequence[dict[str, Any]], path: Path) -> None:
    """Render 30 family deltas as a labeled 6x5 diverging heatmap."""
    ordered = sorted(families, key=lambda row: (-row["absolute_delta_pp"], row["value"]))
    maximum = max(abs(row["absolute_delta_pp"]) for row in ordered)
    cells = []
    for index, row in enumerate(ordered):
        column, line = index % 5, index // 5
        x, y = 30 + column * 230, 100 + line * 74
        value = row["absolute_delta_pp"]
        intensity = int(55 + 160 * abs(value) / maximum)
        color = (
            f"rgb({235 - intensity // 3},{245 - intensity // 2},{255 - intensity})"
            if value >= 0
            else f"rgb({255 - intensity},{238 - intensity // 2},{230 - intensity // 3})"
        )
        cells.append(
            f'<rect x="{x}" y="{y}" width="216" height="61" rx="5" fill="{color}"/>'
            f'<text x="{x + 8}" y="{y + 23}" class="l">{html.escape(row["value"][:28])}</text>'
            f'<text x="{x + 8}" y="{y + 47}" class="v">{value:+.2f} pp</text>'
        )
    document = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="620">'
        "<style>.t{font:700 25px system-ui;fill:#0f172a}.s{font:14px system-ui;fill:#475569}"
        ".l{font:11px system-ui;fill:#0f172a}.v{font:700 13px system-ui;fill:#0f172a}</style>"
        '<rect width="1200" height="620" fill="#f8fafc"/>'
        '<text x="30" y="40" class="t">P02 Family delta heatmap</text>'
        f'<text x="30" y="67" class="s">{html.escape(BOUNDARY)}</text>'
        + "".join(cells)
        + '<text x="30" y="590" class="s">Sorted C1 minus B2 percentage points; blue positive, red negative.</text></svg>\n'
    )
    write_text(path, document)


def forest_svg(families: Sequence[dict[str, Any]], path: Path) -> None:
    """Render sorted family B2/C1 rates as paired descriptive points."""
    ordered = sorted(families, key=lambda row: (-row["absolute_delta_pp"], row["value"]))
    content = []
    for index, row in enumerate(ordered):
        y = 92 + index * 16
        b2_x, c1_x = 415 + 720 * row["b2_success_rate"], 415 + 720 * row["c1_success_rate"]
        content.append(
            f'<text x="400" y="{y + 4}" class="l" text-anchor="end">{html.escape(row["value"][:32])}</text>'
            f'<line x1="{b2_x:.1f}" y1="{y}" x2="{c1_x:.1f}" y2="{y}" stroke="#94a3b8"/>'
            f'<circle cx="{b2_x:.1f}" cy="{y}" r="4" fill="#64748b"/>'
            f'<circle cx="{c1_x:.1f}" cy="{y}" r="4" fill="#0f766e"/>'
        )
    document = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="620">'
        "<style>.t{font:700 25px system-ui;fill:#0f172a}.s{font:14px system-ui;fill:#475569}"
        '.l{font:10px system-ui;fill:#1e293b}</style><rect width="1200" height="620" fill="#f8fafc"/>'
        '<text x="30" y="35" class="t">P03 Family success comparison</text>'
        f'<text x="30" y="59" class="s">{html.escape(BOUNDARY)}</text>'
        + "".join(content)
        + '<circle cx="930" cy="585" r="4" fill="#64748b"/><text x="940" y="589" class="s">B2</text>'
        '<circle cx="990" cy="585" r="4" fill="#0f766e"/><text x="1000" y="589" class="s">C1</text></svg>\n'
    )
    write_text(path, document)


def behavior_confusion_svg(rows_: Sequence[dict[str, Any]], path: Path) -> None:
    """Render observed behavior distributions for each expected behavior and method."""
    expected = ["ANSWER", "CLARIFY", "REFRESH", "REFUSE", "RETRY", "ABSTAIN"]
    observed = expected + ["UNKNOWN"]
    parts = []
    for method_index, method in enumerate(("b2", "c1")):
        x0 = 102 + method_index * 555
        parts.append(f'<text x="{x0}" y="91" class="s">{method.upper()}</text>')
        for line, exp in enumerate(expected):
            subset = [row for row in rows_ if row["expected_behavior"] == exp]
            counts = Counter(row[f"{method}_observed_behavior"] for row in subset)
            for column, obs in enumerate(observed):
                count = counts[obs]
                intensity = int(245 - 190 * count / max(len(subset), 1))
                x, y = x0 + column * 65, 112 + line * 62
                parts.append(
                    f'<rect x="{x}" y="{y}" width="58" height="54" fill="rgb({intensity},{intensity + 5},{255})"/>'
                    f'<text x="{x + 29}" y="{y + 32}" class="v" text-anchor="middle">{count}</text>'
                )
            parts.append(
                f'<text x="{x0 - 8}" y="{143 + line * 62}" class="l" text-anchor="end">{exp}</text>'
            )
        for column, obs in enumerate(observed):
            parts.append(
                f'<text x="{x0 + 29 + column * 65}" y="505" class="l" text-anchor="middle" transform="rotate(-45 {x0 + 29 + column * 65} 505)">{obs}</text>'
            )
    document = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="620">'
        "<style>.t{font:700 25px system-ui;fill:#0f172a}.s{font:14px system-ui;fill:#475569}"
        ".l{font:10px system-ui;fill:#1e293b}.v{font:700 12px system-ui;fill:#0f172a}</style>"
        '<rect width="1200" height="620" fill="#f8fafc"/><text x="30" y="35" class="t">P04 Behavior confusion</text>'
        f'<text x="30" y="59" class="s">{html.escape(BOUNDARY)}</text>'
        + "".join(parts)
        + '<text x="30" y="598" class="s">Rows are expected behavior; columns are stored observed behavior.</text></svg>\n'
    )
    write_text(path, document)


def make_figures(
    rows_: Sequence[dict[str, Any]],
    families: Sequence[dict[str, Any]],
    lofo_: dict[str, Any],
    bootstrap_: dict[str, Any],
    concentration_: dict[str, Any],
    backlog_: Sequence[dict[str, Any]],
) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    cells = Counter(x["paired_transition"] for x in rows_)
    labels = ["BOTH_CORRECT", "C1_ONLY", "B2_ONLY", "BOTH_WRONG"]
    svg(
        "P01 Overall paired transitions",
        labels,
        [("tasks", [cells[x] for x in labels], "#2563eb")],
        FIGURES / "P01_overall_transition.svg",
    )
    heatmap_svg(families, FIGURES / "P02_family_delta_heatmap.svg")
    forest_svg(families, FIGURES / "P03_family_success_comparison.svg")
    behavior_confusion_svg(rows_, FIGURES / "P04_behavior_confusion.svg")
    errors = sorted({x["c1_error_class"] for x in rows_})
    svg(
        "P05 Error taxonomy",
        errors,
        [
            ("B2", [sum(x["b2_error_class"] == e for x in rows_) for e in errors], "#64748b"),
            ("C1", [sum(x["c1_error_class"] == e for x in rows_) for e in errors], "#dc2626"),
        ],
        FIGURES / "P05_error_taxonomy.svg",
    )
    specs = [
        ("difficulty", "P06 Difficulty slices", "P06_difficulty_slices.svg"),
        ("source", "P07 Source slices", "P07_source_slices.svg"),
        ("required_tables_count", "P08 Complexity slices", "P08_complexity_slices.svg"),
    ]
    for dimension, title, filename in specs:
        values = sorted({str(x[dimension]) for x in rows_})
        groups = [[x for x in rows_ if str(x[dimension]) == value] for value in values]
        svg(
            title,
            values,
            [
                ("B2", [sum(x["b2_correct"] for x in g) / len(g) for g in groups], "#64748b"),
                ("C1", [sum(x["c1_correct"] for x in g) / len(g) for g in groups], "#0f766e"),
            ],
            FIGURES / filename,
            1,
        )
    lofo_rows = lofo_["rows"]
    svg(
        "P09 Leave-one-family-out delta",
        [x["removed_family"] for x in lofo_rows],
        [("delta", [x["paired_delta"] for x in lofo_rows], "#ea580c")],
        FIGURES / "P09_lofo_delta.svg",
    )
    hist = bootstrap_["histogram"]
    centers = [(a + b) / 2 for a, b in zip(hist["edges"][:-1], hist["edges"][1:])]
    svg(
        "P10 Family bootstrap delta",
        [f"{x:.2f}" for x in centers],
        [("replicates", hist["counts"], "#2563eb")],
        FIGURES / "P10_bootstrap_delta.svg",
    )
    for key, name, title in (
        ("positive_net_wins", "P11_win_concentration.svg", "P11 Win concentration"),
        ("c1_failures", "P12_failure_concentration.svg", "P12 Failure concentration"),
    ):
        shares = concentration_[key]["top_shares"]
        svg(title, list(shares), [("share", list(shares.values()), "#7c3aed")], FIGURES / name, 1)
    coverage = [
        [x for x in rows_ if bool(x["retrieval_complete_at_candidate_k"]) == value]
        for value in (False, True)
    ]
    svg(
        "P13 Retrieval coverage and success",
        ["incomplete", "complete"],
        [
            (
                "B2",
                [sum(x["b2_correct"] for x in g) / len(g) if g else 0 for g in coverage],
                "#64748b",
            ),
            (
                "C1",
                [sum(x["c1_correct"] for x in g) / len(g) if g else 0 for g in coverage],
                "#0f766e",
            ),
        ],
        FIGURES / "P13_retrieval_success_relation.svg",
        1,
    )
    quartile_groups = [
        [x for x in rows_ if x["c1_context_quartile"] == q] for q in ("Q1", "Q2", "Q3", "Q4")
    ]
    svg(
        "P14 Context size and success",
        ["Q1", "Q2", "Q3", "Q4"],
        [("C1", [sum(x["c1_correct"] for x in g) / len(g) for g in quartile_groups], "#0f766e")],
        FIGURES / "P14_context_success_relation.svg",
        1,
    )
    top = list(backlog_[:10])
    svg(
        "P15 Improvement backlog",
        [x["issue"] for x in top],
        [("impact", [x["impact"] for x in top], "#b91c1c")],
        FIGURES / "P15_improvement_backlog.svg",
    )


def header(title: str) -> str:
    return f"# {title}\n\n> **{BOUNDARY}**\n\nAnalysis identity: {IDENTITY}. Parent: {TAG} at {PARENT}.\n\n"


def table(values: Sequence[dict[str, Any]], columns: Sequence[str]) -> str:
    output = "| " + " | ".join(columns) + " |\n|" + "|".join("---" for _ in columns) + "|\n"
    for row in values:
        output += "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |\n"
    return output


def make_reports(
    rows_: Sequence[dict[str, Any]],
    slices: list[dict[str, Any]],
    families: list[dict[str, Any]],
    behaviors: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    detail: dict[str, Any],
    lofo_: dict[str, Any],
    bootstrap_: dict[str, Any],
    concentration_: dict[str, Any],
    backlog_: list[dict[str, Any]],
    metadata: dict[str, Any],
    tests: list[dict[str, Any]],
) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    overall = slice_row("overall", "ALL", rows_)
    best = sorted(families, key=lambda row: (-row["net_paired_wins"], row["value"]))[:5]
    worst = sorted(families, key=lambda row: (row["net_paired_wins"], row["value"]))[:5]
    b2_unsafe = sum(
        row["count"]
        for row in behaviors
        if row["method"] == "B2" and row["diagnostic"] == "UNSAFE_ANSWER"
    )
    c1_unsafe = sum(
        row["count"]
        for row in behaviors
        if row["method"] == "C1" and row["diagnostic"] == "UNSAFE_ANSWER"
    )
    write_text(
        REPORTS / "POSTHOC_DIAGNOSTIC_REPORT.md",
        header("Post-hoc diagnostic report")
        + f"## Scope\n\nVerified 360 paired tasks, 30 families x 12, B2 200/360, C1 247/360, C1-only 75, B2-only 28, and net wins 47. The observed {overall['absolute_delta_pp']:.4f} percentage-point delta remains qualification-only.\n\n## Descriptive findings\n\nThe 103 discordant pairs comprise 75 C1-only and 28 B2-only outcomes. Family effects ranged from {min(x['absolute_delta_pp'] for x in families):.2f} to {max(x['absolute_delta_pp'] for x in families):.2f} percentage points. Stored-output classification found {b2_unsafe} B2 and {c1_unsafe} C1 unsafe-answer diagnostics. These counts are operational diagnostics and do not establish security performance.\n\nLargest positive family net contributions:\n\n"
        + table(best, ("value", "b2_correct", "c1_correct", "net_paired_wins", "absolute_delta_pp"))
        + "\nLargest negative family net contributions:\n\n"
        + table(
            worst, ("value", "b2_correct", "c1_correct", "net_paired_wins", "absolute_delta_pp")
        )
        + "\n## Availability\n\nContext tokens and stored top-20 rerankings are available. Per-task latency, pre-reranker ranks, and selected-context identities are unavailable. Stored latency comprises 90 four-task batches per method and is not production latency.\n\n## Governance\n\nNo inference or retrieval ran. No task, protected artifact, freeze, RUN_STATE field, release receipt, or release tag was modified. Exploratory results cannot reverse v2 E07.\n",
    )
    major = [
        x
        for x in slices
        if x["dimension"]
        in {"expected_behavior", "difficulty", "source", "task_mode", "independent_review_member"}
    ]
    write_text(
        REPORTS / "SLICE_ANALYSIS.md",
        header("Slice analysis")
        + table(
            major,
            (
                "dimension",
                "value",
                "n",
                "flag",
                "b2_success_rate",
                "c1_success_rate",
                "absolute_delta_pp",
                "net_paired_wins",
            ),
        )
        + "\n## All semantic families\n\n"
        + table(
            families,
            (
                "value",
                "n",
                "b2_correct",
                "c1_correct",
                "b2_success_rate",
                "c1_success_rate",
                "absolute_delta_pp",
                "c1_only",
                "b2_only",
                "both_wrong",
                "discordance_rate",
                "net_paired_wins",
                "flag",
            ),
        )
        + "\nExact McNemar p values and BH q values are exploratory. Slices below 20 or with fewer than 10 discordant pairs were not tested.\n\n"
        + table(tests, ("dimension", "value", "n", "mcnemar_exact_p", "bh_fdr_q")),
    )
    overall_errors = [x for x in errors if x["dimension"] == "overall"]
    write_text(
        REPORTS / "ERROR_ANALYSIS.md",
        header("Error analysis")
        + "Taxonomy uses stored fields only; hidden reasoning and causal mechanisms are not inferred.\n\n"
        + table(overall_errors, ("method", "error_type", "count", "rate"))
        + "\nUnsafe answers are operationally critical diagnostics, not security certification.\n\n"
        + table(
            behaviors,
            ("method", "expected", "observed", "diagnostic", "count", "rate_within_expected"),
        )
        + "\n## Highest-volume C1 failure cells\n\n"
        + table(
            detail["highest_volume_failure_cells"][:10],
            ("dimension", "slice", "error_type", "count", "rate"),
        )
        + "\n## Highest-rate C1 failure cells\n\n"
        + table(
            detail["highest_rate_failure_cells"][:10],
            ("dimension", "slice", "error_type", "count", "rate"),
        )
        + f"\nMachine-readable outputs include {len(detail['error_transitions'])} error transitions and root-cause cross-tabs. Cell labels describe associations in stored fields, not causal root causes.\n",
    )
    retrieval_slices = grouped(
        rows_,
        (
            "retrieval_complete_at_candidate_k",
            "retrieval_coverage_bin",
            "retrieval_first_required_rank_bin",
            "c1_context_quartile",
            "c1_context_saturated",
        ),
    )
    write_text(
        REPORTS / "RETRIEVAL_CONTEXT_ANALYSIS.md",
        header("Retrieval and context analysis")
        + "Coverage compares required IDs with stored top-20 rankings. Association does not prove causation. Rank shifts are unavailable.\n\n"
        + table(
            retrieval_slices,
            ("dimension", "value", "n", "b2_success_rate", "c1_success_rate", "c1_only", "b2_only"),
        )
        + "\n## Missingness\n\n"
        + json.dumps(metadata["missingness"], indent=2)
        + "\n\n## Compute timing scope\n\n"
        + metadata["latency_scope"]
        + ". Stored batch percentiles:\n\n```json\n"
        + json.dumps(metadata["batch_latency_seconds"], indent=2)
        + "\n```\n\nThese qualification batch timings cannot be interpreted as per-task or production latency.\n",
    )
    write_text(
        REPORTS / "ROBUSTNESS_ANALYSIS.md",
        header("Robustness analysis")
        + f"LOFO delta range: {lofo_['minimum_delta']:.6f} to {lofo_['maximum_delta']:.6f}; mean {lofo_['mean_delta']:.6f}; median {lofo_['median_delta']:.6f}. Most influential positive family: {lofo_['most_influential_positive_family']}; negative: {lofo_['most_influential_negative_family']}.\n\nThe 100,000-replicate family bootstrap percentile interval is {bootstrap_['percentile_interval_95']}; P(delta>0)={bootstrap_['probability_delta_gt_zero']:.6f}; P(delta>-0.05)={bootstrap_['probability_delta_gt_negative_0_05']:.6f}. These are POSTHOC EXPLORATORY.\n\nConcentration:\n\n"
        + json.dumps(concentration_, indent=2)
        + "\n",
    )
    write_text(
        REPORTS / "IMPROVEMENT_BACKLOG.md",
        header("Improvement backlog")
        + "Impact equals frequency x severity x confidence. Subsystem assignments are hypotheses, not causal findings. Every mitigation requires a new scientific protocol.\n\n"
        + table(
            backlog_,
            (
                "issue",
                "frequency",
                "severity",
                "confidence",
                "impact",
                "likely_subsystem",
                "affected_slice_count",
                "evidence",
                "proposed_mitigation",
                "requires_new_scientific_protocol",
            ),
        ),
    )
    write_text(
        REPORTS / "POSTHOC_CLAIM_LEDGER.md",
        header("Post-hoc claim ledger")
        + "| Claim | Disposition |\n|---|---|\n| C1 is confirmed better | Prohibited; +13.06 pp is qualification-only. |\n| Bootstrap reverses E07 | Prohibited. |\n| A slice is confirmed | Prohibited; p and q values are exploratory. |\n| Retrieval caused an error | Unsupported; association only. |\n| Batch latency is production latency | Prohibited. |\n| Unsafe-answer counts certify security | Prohibited. |\n| Closed v2 state changed | False. |\n",
    )


def generate() -> dict[str, Any]:
    canonical = verify_release()
    DATA.mkdir(parents=True, exist_ok=True)
    master, metadata = master_table()
    dimensions = (
        "semantic_family",
        "family",
        "expected_behavior",
        "difficulty",
        "source",
        "task_mode",
        "independent_review_member",
        "schema_version",
        "metric_version",
        "required_tables_count",
        "required_columns_count",
        "required_metrics_count",
        "required_docs_count",
        "dependency_count",
        "graph_distance",
        "query_length_quartile",
        "b2_context_quartile",
        "c1_context_quartile",
        "gold_join_complexity",
        "aggregation_or_window",
        "temporal_indicator",
        "ratio_nested_metric_indicator",
        "policy_document_indicator",
        "ambiguity_indicator",
        "freshness_indicator",
        "authorization_indicator",
        "schema_drift_indicator",
        "cache_retry_indicator",
        "retrieval_coverage_bin",
        "retrieval_first_required_rank_bin",
    )
    slices = grouped(master, dimensions)
    test_rows = tests_with_fdr(slices)
    families = family_table(master)
    behaviors = behavior_table(master)
    errors, detail = error_tables(master)
    lofo_result = lofo(families)
    bootstrap_result = bootstrap(families)
    concentration_result = concentration(families)
    backlog_result = backlog(master)
    write_csv(DATA / "task_master.csv", master)
    temporary = DATA / "task_master.parquet.tmp"
    pq.write_table(pa.Table.from_pylist(master), temporary, compression="zstd", version="2.6")
    temporary.replace(DATA / "task_master.parquet")
    write_json(
        DATA / "slices.json",
        {
            "identity": IDENTITY,
            "classification": "POSTHOC_EXPLORATORY",
            "metadata": metadata,
            "slices": slices,
            "exploratory_mcnemar_bh": test_rows,
            **detail,
        },
    )
    write_csv(DATA / "family_analysis.csv", families)
    write_csv(DATA / "behavior_analysis.csv", behaviors)
    write_csv(DATA / "error_taxonomy.csv", errors)
    write_json(DATA / "lofo.json", lofo_result)
    write_json(DATA / "bootstrap.json", bootstrap_result)
    write_json(DATA / "concentration.json", concentration_result)
    write_json(
        DATA / "improvement_backlog.json",
        {"identity": IDENTITY, "classification": "POSTHOC_EXPLORATORY", "issues": backlog_result},
    )
    make_figures(
        master, families, lofo_result, bootstrap_result, concentration_result, backlog_result
    )
    make_reports(
        master,
        slices,
        families,
        behaviors,
        errors,
        detail,
        lofo_result,
        bootstrap_result,
        concentration_result,
        backlog_result,
        metadata,
        test_rows,
    )
    paths = sorted([*DATA.glob("*"), *REPORTS.glob("*"), *FIGURES.glob("*")])
    paths = [path for path in paths if path.is_file() and path.name != "manifest.json"]
    artifacts = {path.relative_to(ROOT).as_posix(): sha(path.read_bytes()) for path in paths}
    manifest: dict[str, Any] = {
        "analysis_identity": IDENTITY,
        "classification": "post-release exploratory descriptive qualification-data-only",
        "parent_release_tag": TAG,
        "parent_release_commit": PARENT,
        "boundary": BOUNDARY,
        "canonical_inputs": canonical,
        "validation": {
            "paired_rows": 360,
            "families": 30,
            "tasks_per_family": 12,
            "b2_correct": 200,
            "c1_correct": 247,
            "c1_only": 75,
            "b2_only": 28,
            "net_wins": 47,
        },
        "execution": {
            "seed": SEED,
            "bootstrap_replicates": REPLICATES,
            "gpu_used": False,
            "model_inference_run": False,
            "retrieval_run": False,
            "protected_data_read": False,
            "run_state_modified": False,
            "release_artifacts_overwritten": False,
        },
        "artifacts": artifacts,
        "manifest_hash_scope": "canonical payload hash; self-file hash excluded to avoid recursion",
    }
    manifest["manifest_payload_sha256"] = sha(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    )
    write_json(DATA / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2, sort_keys=True))
