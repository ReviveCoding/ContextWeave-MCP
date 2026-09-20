"""Paired pilot analysis and prespecified non-inferiority sample sizing."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from typing import Any

from scipy.stats import norm  # type: ignore[import-untyped]

from contextweave.evidence import ROOT, atomic_json, record, utc_now

DESIGN: dict[str, Any] = {
    "primary_unit": "task",
    "comparison": "selected ContextWeave vs strongest eligible frozen baseline",
    "noninferiority_margin_absolute_success": 0.05,
    "one_sided_alpha": 0.025,
    "target_power": 0.90,
    "material_context_reduction_fraction": 0.20,
    "bootstrap_replicates": 10000,
    "bootstrap_seed": 20260920,
    "latency_outer_unit": "process/server replicate",
    "secondary_multiplicity": "Holm",
    "feasible_max_locked_tasks": 600,
    "family_cluster_sensitivity": "required N is the larger of task-paired and semantic-family-cluster estimates",
    "protected_reuse": "one shot",
}


def _load(method: str) -> dict[str, dict[str, Any]]:
    path = ROOT / f"evidence/pilot/{method.lower()}_qwen3_4b.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    by_id = {row["task_id"]: row for row in rows}
    if len(by_id) != len(rows) or any(row["method"] != method for row in rows):
        raise ValueError(f"{method} pilot has duplicate task IDs or mismatched method identity")
    return by_id


def plan_power() -> dict[str, Any]:
    started = utc_now()
    b2 = _load("B2")
    c1 = _load("C1")
    task_manifest = json.loads(
        (ROOT / "benchmarks/pilot_manifest.json").read_text(encoding="utf-8")
    )
    task_file = ROOT / "benchmarks/pilot_programmatic.jsonl"
    expected_identity = task_manifest["task_file_sha256"]
    if hashlib.sha256(task_file.read_bytes()).hexdigest() != expected_identity:
        raise ValueError("frozen pilot task file changed")
    tasks = [
        json.loads(line) for line in task_file.read_text(encoding="utf-8").splitlines() if line
    ]
    expected_ids = {task["task_id"] for task in tasks}
    if len(expected_ids) != len(tasks) or len(tasks) != task_manifest["task_count"]:
        raise ValueError("frozen pilot task set is invalid")
    task_ids = set(b2) & set(c1)
    if task_ids != expected_ids or set(b2) != expected_ids or set(c1) != expected_ids:
        raise ValueError("paired pilot outcomes incomplete")
    if any(
        row["task_manifest_sha256"] != expected_identity for row in (*b2.values(), *c1.values())
    ):
        raise ValueError("paired pilot task identity mismatch")
    if any(
        row["device"] != "cuda"
        or row["model_revision"] != "1cfa9a7208912126459214e8b04321603b3df60c"
        for row in (*b2.values(), *c1.values())
    ):
        raise ValueError("paired pilot CUDA or model identity mismatch")
    n = len(task_ids)
    family_by_id = {task["task_id"]: task["semantic_family"] for task in tasks}
    family_differences: dict[str, list[int]] = {}
    for key in sorted(task_ids):
        family_differences.setdefault(family_by_id[key], []).append(
            int(c1[key]["status"] == "CORRECT") - int(b2[key]["status"] == "CORRECT")
        )
    family_effects = {
        family: {"task_count": len(differences), "paired_difference": statistics.mean(differences)}
        for family, differences in sorted(family_differences.items())
    }
    family_effect_variance = statistics.variance(
        [value["paired_difference"] for value in family_effects.values()]
    )
    candidate_only = sum(
        c1[key]["status"] == "CORRECT" and b2[key]["status"] != "CORRECT" for key in task_ids
    )
    baseline_only = sum(
        b2[key]["status"] == "CORRECT" and c1[key]["status"] != "CORRECT" for key in task_ids
    )
    delta = (candidate_only - baseline_only) / n
    discordance = (candidate_only + baseline_only) / n
    variance = max(discordance - delta * delta, 1 / n)
    family_cluster_variance = max(family_effect_variance * n / len(family_effects), 1 / n)
    margin = DESIGN["noninferiority_margin_absolute_success"]
    if delta + margin > 0:
        z_sum_sq = (norm.ppf(1 - DESIGN["one_sided_alpha"]) + norm.ppf(DESIGN["target_power"])) ** 2
        n_required_task = math.ceil(z_sum_sq * variance / (delta + margin) ** 2)
        n_required_family = math.ceil(z_sum_sq * family_cluster_variance / (delta + margin) ** 2)
        n_required = max(n_required_task, n_required_family)
    else:
        n_required_task = None
        n_required_family = None
        n_required = None
    feasible = n_required is not None and n_required <= DESIGN["feasible_max_locked_tasks"]
    result = {
        "timestamp_utc": utc_now(),
        "design": DESIGN,
        "pilot_tasks": n,
        "B2_success": sum(row["status"] == "CORRECT" for row in b2.values()),
        "C1_success": sum(row["status"] == "CORRECT" for row in c1.values()),
        "candidate_only": candidate_only,
        "baseline_only": baseline_only,
        "paired_difference": delta,
        "discordance": discordance,
        "variance_estimate": variance,
        "family_effects": family_effects,
        "family_effect_variance": family_effect_variance,
        "family_cluster_variance_per_task": family_cluster_variance,
        "required_locked_n_task_paired": n_required_task,
        "required_locked_n_family_sensitivity": n_required_family,
        "required_locked_n": n_required,
        "feasible": feasible,
        "status": "DESIGN_READY" if feasible else "INSUFFICIENT_POWER",
        "pilot_task_manifest_sha256": expected_identity,
        "evidence_class": "Q",
        "note": "Normal approximation and six-family variance are conservative planning estimates, not locked hypothesis results. Assess family diversity and protected split construction before design freeze.",
    }
    rel = "evidence/power/paired_design.json"
    atomic_json(ROOT / rel, result)
    record(
        "E07",
        "E07-paired-power",
        DESIGN,
        {"pilot_tasks": expected_identity},
        {"device_backend": "CPU", "scipy": "1.18.1"},
        "PASS" if feasible else "GATED",
        [rel],
        "Q",
        started,
        reason=None
        if feasible
        else "Required paired/cluster-sensitive N exceeds feasible 600 or NI planning effect is nonpositive",
    )
    return result


if __name__ == "__main__":
    print(json.dumps(plan_power(), indent=2))
