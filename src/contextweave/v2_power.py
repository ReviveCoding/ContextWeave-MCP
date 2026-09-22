"""Family-clustered analytic and simulation power planning for v2."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, cast

import numpy as np
from scipy.stats import nct, norm, t

from contextweave.evidence import ROOT, atomic_json, utc_now

MARGIN = 0.05
ALPHA = 0.025
TARGET_POWER = 0.90
CEILING = 600
REPLICATES = 10_000
SEED = 20260922


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _reject(family_means: np.ndarray[Any, Any], margin: float = MARGIN) -> np.ndarray[Any, Any]:
    k = family_means.shape[1]
    means = family_means.mean(axis=1)
    sd = family_means.std(axis=1, ddof=1)
    statistic = np.divide(
        means + margin,
        sd / math.sqrt(k),
        out=np.where(means + margin > 0, np.full_like(means, np.inf), np.full_like(means, -np.inf)),
        where=sd > 0,
    )
    return cast(np.ndarray[Any, Any], statistic > t.ppf(1 - ALPHA, k - 1))


def _simulate(
    base: np.ndarray[Any, Any],
    k: int,
    tasks_per_family: int,
    target_delta: float,
    heterogeneity_multiplier: float,
    rng: np.random.Generator,
) -> float:
    # base columns: both correct, C1 only, B2 only, neither.
    discordance = base[:, 1] + base[:, 2]
    differences = base[:, 1] - base[:, 2]
    centered = (differences - differences.mean()) * heterogeneity_multiplier + target_delta
    centered = np.clip(centered, -discordance, discordance)
    adjusted = base.copy()
    adjusted[:, 1] = (discordance + centered) / 2
    adjusted[:, 2] = (discordance - centered) / 2
    adjusted /= adjusted.sum(axis=1, keepdims=True)
    family_indices = rng.integers(0, len(adjusted), size=(REPLICATES, k))
    concentration = tasks_per_family + 4
    alpha = adjusted[family_indices] * concentration + 0.5
    gamma = rng.gamma(alpha, 1.0)
    probabilities = gamma / gamma.sum(axis=2, keepdims=True)
    counts = rng.multinomial(tasks_per_family, probabilities)
    means = (counts[:, :, 1] - counts[:, :, 2]) / tasks_per_family
    return float(_reject(means).mean())


def plan() -> dict[str, Any]:
    manifest = json.loads((ROOT / "benchmarks/v2_pilot_manifest.json").read_text())
    task_path = ROOT / "benchmarks/v2_pilot_tasks.jsonl"
    identity = hashlib.sha256(task_path.read_bytes()).hexdigest()
    if identity != manifest["task_file_sha256"]:
        raise RuntimeError("v2 task identity changed")
    tasks = _rows(task_path)
    b2_rows = _rows(ROOT / "evidence/pilot_v2/b2_qwen3_4b.jsonl")
    c1_rows = _rows(ROOT / "evidence/pilot_v2/c1_qwen3_4b.jsonl")
    b2 = {x["task_id"]: x for x in b2_rows}
    c1 = {x["task_id"]: x for x in c1_rows}
    ids = [x["task_id"] for x in tasks]
    if len(b2) != 360 or len(c1) != 360 or set(b2) != set(ids) or set(c1) != set(ids):
        raise RuntimeError("v2 paired outcomes incomplete")
    family_by_id = {x["task_id"]: x["semantic_family"] for x in tasks}
    family_differences: dict[str, list[int]] = defaultdict(list)
    family_cells: dict[str, Counter[str]] = defaultdict(Counter)
    candidate_only = baseline_only = 0
    for task_id in ids:
        b = b2[task_id]["status"] == "CORRECT"
        c = c1[task_id]["status"] == "CORRECT"
        candidate_only += int(c and not b)
        baseline_only += int(b and not c)
        family = family_by_id[task_id]
        family_differences[family].append(int(c) - int(b))
        family_cells[family][
            ("both" if b and c else "c1_only" if c else "b2_only" if b else "neither")
        ] += 1
    family_means = [statistics.mean(values) for values in family_differences.values()]
    mean_difference = statistics.mean(family_means)
    family_sd = statistics.stdev(family_means)
    task_discordance = (candidate_only + baseline_only) / len(ids)
    task_delta = (candidate_only - baseline_only) / len(ids)
    task_variance = max(task_discordance - task_delta**2, 1 / len(ids))
    z2 = (norm.ppf(1 - ALPHA) + norm.ppf(TARGET_POWER)) ** 2
    task_required = math.ceil(z2 * task_variance / (0 + MARGIN) ** 2)
    analytic_grid: list[dict[str, Any]] = []
    required_families = None
    for k in range(2, 201):
        df = k - 1
        noncentrality = math.sqrt(k) * MARGIN / max(family_sd, 1e-12)
        power = float(nct.sf(t.ppf(1 - ALPHA, df), df, noncentrality))
        if 24 <= k <= 36:
            analytic_grid.append({"family_count": k, "power_at_true_delta_zero": power})
        if required_families is None and power >= TARGET_POWER:
            required_families = k
    base = np.array(
        [
            [cells["both"], cells["c1_only"], cells["b2_only"], cells["neither"]]
            for _, cells in sorted(family_cells.items())
        ],
        dtype=np.float64,
    )
    base /= base.sum(axis=1, keepdims=True)
    rng = np.random.default_rng(SEED)
    simulation: list[dict[str, Any]] = []
    for k in range(24, 37):
        for m in (10, 12, 16, 20):
            if k * m > CEILING:
                continue
            power = _simulate(base, k, m, 0.0, 1.0, rng)
            power_inflated = _simulate(base, k, m, 0.0, 1.5, rng)
            type_i = _simulate(base, k, m, -MARGIN, 1.0, rng)
            mc_se_power = math.sqrt(power * (1 - power) / REPLICATES)
            mc_se_type_i = math.sqrt(max(type_i * (1 - type_i), 1e-12) / REPLICATES)
            simulation.append(
                {
                    "family_count": k,
                    "tasks_per_family": m,
                    "total_tasks": k * m,
                    "power_true_delta_zero": power,
                    "power_heterogeneity_x1_5": power_inflated,
                    "type_i_error_at_margin_boundary": type_i,
                    "power_lower_95_mc": power - 1.96 * mc_se_power,
                    "inflated_power_lower_95_mc": power_inflated
                    - 1.96 * math.sqrt(power_inflated * (1 - power_inflated) / REPLICATES),
                    "type_i_upper_95_mc": type_i + 1.96 * mc_se_type_i,
                }
            )
    eligible = [
        row
        for row in simulation
        if row["power_lower_95_mc"] >= TARGET_POWER
        and row["inflated_power_lower_95_mc"] >= TARGET_POWER
        and row["type_i_upper_95_mc"] <= ALPHA + 1.96 * math.sqrt(ALPHA * (1 - ALPHA) / REPLICATES)
    ]
    selected = (
        min(eligible, key=lambda row: (row["total_tasks"], row["family_count"]))
        if eligible
        else None
    )
    result = {
        "timestamp_utc": utc_now(),
        "protocol_identity": manifest["protocol_identity"],
        "status": "DESIGN_READY" if selected else "INSUFFICIENT_POWER",
        "evidence_class": "Q",
        "task_manifest_sha256": identity,
        "pilot_task_count": len(ids),
        "pilot_family_count": len(family_means),
        "B2_success": sum(x["status"] == "CORRECT" for x in b2_rows),
        "C1_success": sum(x["status"] == "CORRECT" for x in c1_rows),
        "candidate_only": candidate_only,
        "baseline_only": baseline_only,
        "task_paired_difference": task_delta,
        "task_discordance": task_discordance,
        "task_level_required_n_at_true_delta_zero": task_required,
        "equal_family_weighted_difference": mean_difference,
        "between_family_sd": family_sd,
        "between_family_variance": family_sd**2,
        "family_means": dict(
            sorted((key, statistics.mean(value)) for key, value in family_differences.items())
        ),
        "analytic": {
            "estimand": "equal-family-weighted paired TaskSuccess difference",
            "reference_distribution": "one-sample noncentral t",
            "degrees_of_freedom": "K-1",
            "planning_true_difference": 0.0,
            "required_family_count": required_families,
            "grid_24_to_36": analytic_grid,
        },
        "simulation": {
            "replicates": REPLICATES,
            "seed": SEED,
            "paired_cell_model": "family empirical four-cell probabilities centered to planning delta with Dirichlet uncertainty",
            "heterogeneity_sensitivity_multiplier": 1.5,
            "grid": simulation,
            "selected_feasible_design": selected,
        },
        "design": {
            "noninferiority_margin_absolute_success": MARGIN,
            "one_sided_alpha": ALPHA,
            "target_power": TARGET_POWER,
            "feasible_ceiling_tasks": CEILING,
            "family_count_range": [24, 36],
            "tasks_per_family_range": [10, 20],
        },
        "protected_accesses": [],
        "note": "Qualification planning only. No protected benchmark or efficacy result exists.",
    }
    atomic_json(ROOT / "evidence/power_v2/clustered_design.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(plan(), indent=2))
