"""Paired pilot analysis and prespecified non-inferiority sample sizing."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from scipy.stats import norm

from contextweave.evidence import ROOT, atomic_json, record, utc_now

DESIGN = {
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
    "protected_reuse": "one shot",
}


def _load(method: str) -> dict[str, dict[str, Any]]:
    path = ROOT / f"evidence/pilot/{method.lower()}_qwen3_4b.jsonl"
    return {row["task_id"]: row for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)}


def plan_power() -> dict[str, Any]:
    started = utc_now()
    b2 = _load("B2")
    c1 = _load("C1")
    task_manifest = json.loads((ROOT / "benchmarks/pilot_manifest.json").read_text(encoding="utf-8"))
    task_ids = set(b2) & set(c1)
    if len(task_ids) != task_manifest["task_count"] or set(b2) != set(c1):
        raise ValueError("paired pilot outcomes incomplete")
    expected_identity = task_manifest["task_file_sha256"]
    if any(row["task_manifest_sha256"] != expected_identity for row in (*b2.values(), *c1.values())):
        raise ValueError("paired pilot task identity mismatch")
    n = len(task_ids)
    candidate_only = sum(c1[key]["status"] == "CORRECT" and b2[key]["status"] != "CORRECT" for key in task_ids)
    baseline_only = sum(b2[key]["status"] == "CORRECT" and c1[key]["status"] != "CORRECT" for key in task_ids)
    delta = (candidate_only - baseline_only) / n
    discordance = (candidate_only + baseline_only) / n
    variance = max(discordance - delta * delta, 1 / n)
    margin = DESIGN["noninferiority_margin_absolute_success"]
    if delta + margin > 0:
        n_required = math.ceil((norm.ppf(1 - DESIGN["one_sided_alpha"]) + norm.ppf(DESIGN["target_power"])) ** 2 * variance / (delta + margin) ** 2)
    else:
        n_required = None
    feasible = n_required is not None and n_required <= DESIGN["feasible_max_locked_tasks"]
    result = {
        "timestamp_utc": utc_now(), "design": DESIGN,
        "pilot_tasks": n,
        "B2_success": sum(row["status"] == "CORRECT" for row in b2.values()),
        "C1_success": sum(row["status"] == "CORRECT" for row in c1.values()),
        "candidate_only": candidate_only, "baseline_only": baseline_only,
        "paired_difference": delta, "discordance": discordance,
        "variance_estimate": variance, "required_locked_n": n_required,
        "feasible": feasible,
        "status": "DESIGN_READY" if feasible else "INSUFFICIENT_POWER",
        "pilot_task_manifest_sha256": expected_identity,
        "evidence_class": "Q",
        "note": "Normal approximation is a planning calculation, not a locked hypothesis result. Semantic-family clustering must be assessed before design freeze.",
    }
    rel = "evidence/power/paired_design.json"
    atomic_json(ROOT / rel, result)
    if feasible:
        record(
            "E07", "E07-paired-power", DESIGN,
            {"pilot_tasks": expected_identity}, {"device_backend": "CPU", "scipy": "1.18.1"},
            "PASS", [rel], "Q", started,
        )
    return result


if __name__ == "__main__":
    print(json.dumps(plan_power(), indent=2))
