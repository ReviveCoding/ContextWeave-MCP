"""Calibrated family-clustered non-inferiority planning for v2 E07."""

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
SEED = 20260925
E07_IDENTITY = "ContextWeave-v2-E07-calibrated-family-t-v2"
SHRINKAGE_STRENGTH = 2.0
CALIBRATION_TOLERANCE = 0.0025


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _reject(family_means: np.ndarray[Any, Any], margin: float = MARGIN) -> np.ndarray[Any, Any]:
    """Apply H0: mean <= -margin versus H1: mean > -margin."""
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


def _shrink_profiles(
    base: np.ndarray[Any, Any], tasks_per_pilot_family: int
) -> np.ndarray[Any, Any]:
    """Shrink empirical four-cell profiles toward the pooled profile."""
    pooled = base.mean(axis=0)
    return cast(
        np.ndarray[Any, Any],
        (base * tasks_per_pilot_family + SHRINKAGE_STRENGTH * pooled)
        / (tasks_per_pilot_family + SHRINKAGE_STRENGTH),
    )


def _center_profiles(
    base: np.ndarray[Any, Any], target_delta: float, heterogeneity_multiplier: float
) -> tuple[np.ndarray[Any, Any], dict[str, float]]:
    """Shift clipped family effects so their population mean is exactly target_delta."""
    discordance = base[:, 1] + base[:, 2]
    differences = base[:, 1] - base[:, 2]
    raw = (differences - differences.mean()) * heterogeneity_multiplier
    feasible_low = float((-discordance).mean())
    feasible_high = float(discordance.mean())
    if not feasible_low <= target_delta <= feasible_high:
        raise ValueError(
            f"target delta {target_delta} outside feasible [{feasible_low}, {feasible_high}]"
        )
    low, high = -2.0, 2.0
    for _ in range(100):
        shift = (low + high) / 2
        realized = float(np.clip(raw + shift, -discordance, discordance).mean())
        if realized < target_delta:
            low = shift
        else:
            high = shift
    centered = np.clip(raw + (low + high) / 2, -discordance, discordance)
    adjusted = base.copy()
    adjusted[:, 1] = (discordance + centered) / 2
    adjusted[:, 2] = (discordance - centered) / 2
    if np.any(adjusted < -1e-12) or not np.allclose(adjusted.sum(axis=1), 1.0, atol=1e-12):
        raise RuntimeError("centered paired-cell probabilities are invalid")
    realized_profile_mean = float((adjusted[:, 1] - adjusted[:, 2]).mean())
    if not math.isclose(realized_profile_mean, target_delta, abs_tol=1e-12):
        raise RuntimeError("centered profile mean does not equal requested planning delta")
    diagnostics = {
        "requested_mean_paired_difference": target_delta,
        "realized_profile_mean_paired_difference": realized_profile_mean,
        "minimum_cell_probability": float(adjusted.min()),
        "maximum_probability_sum_error": float(np.abs(adjusted.sum(axis=1) - 1).max()),
        "mean_discordance": float(discordance.mean()),
    }
    return adjusted, diagnostics


def _simulate(
    profiles: np.ndarray[Any, Any],
    k: int,
    tasks_per_family: int,
    rng: np.random.Generator,
    replicates: int = REPLICATES,
) -> dict[str, float]:
    rejected = 0
    paired_difference_sum = 0.0
    chunk_size = 5_000
    for start in range(0, replicates, chunk_size):
        size = min(chunk_size, replicates - start)
        family_indices = rng.integers(0, len(profiles), size=(size, k))
        probabilities = profiles[family_indices]
        counts = rng.multinomial(tasks_per_family, probabilities)
        family_means = (counts[:, :, 1] - counts[:, :, 2]) / tasks_per_family
        rejected += int(_reject(family_means).sum())
        paired_difference_sum += float(family_means.mean(axis=1).sum())
    rate = rejected / replicates
    mc_se = math.sqrt(max(rate * (1 - rate), 1e-12) / replicates)
    return {
        "rejection_rate": rate,
        "realized_mean_paired_difference": paired_difference_sum / replicates,
        "mc_standard_error": mc_se,
        "mc_lower_95": max(0.0, rate - 1.96 * mc_se),
        "mc_upper_95": min(1.0, rate + 1.96 * mc_se),
    }


def plan() -> dict[str, Any]:
    manifest = json.loads((ROOT / "benchmarks/v2_pilot_manifest.json").read_text())
    task_path = ROOT / "benchmarks/v2_pilot_tasks.jsonl"
    identity = hashlib.sha256(task_path.read_bytes()).hexdigest()
    if identity != manifest["task_file_sha256"]:
        raise RuntimeError("v2 task identity changed")
    tasks = _rows(task_path)
    b2_rows = _rows(ROOT / "evidence/pilot_v2/b2_qwen3_4b.jsonl")
    c1_rows = _rows(ROOT / "evidence/pilot_v2/c1_qwen3_4b.jsonl")
    b2 = {row["task_id"]: row for row in b2_rows}
    c1 = {row["task_id"]: row for row in c1_rows}
    ids = [task["task_id"] for task in tasks]
    if len(b2) != 360 or len(c1) != 360 or set(b2) != set(ids) or set(c1) != set(ids):
        raise RuntimeError("v2 paired outcomes incomplete")

    family_by_id = {task["task_id"]: task["semantic_family"] for task in tasks}
    family_differences: dict[str, list[int]] = defaultdict(list)
    family_cells: dict[str, Counter[str]] = defaultdict(Counter)
    candidate_only = baseline_only = 0
    for task_id in ids:
        baseline_success = b2[task_id]["status"] == "CORRECT"
        candidate_success = c1[task_id]["status"] == "CORRECT"
        candidate_only += int(candidate_success and not baseline_success)
        baseline_only += int(baseline_success and not candidate_success)
        family = family_by_id[task_id]
        family_differences[family].append(int(candidate_success) - int(baseline_success))
        family_cells[family][
            (
                "both"
                if baseline_success and candidate_success
                else "c1_only"
                if candidate_success
                else "b2_only"
                if baseline_success
                else "neither"
            )
        ] += 1

    family_means = [statistics.mean(values) for values in family_differences.values()]
    mean_difference = statistics.mean(family_means)
    family_sd = statistics.stdev(family_means)
    task_discordance = (candidate_only + baseline_only) / len(ids)
    task_delta = (candidate_only - baseline_only) / len(ids)
    task_variance = max(task_discordance - task_delta**2, 1 / len(ids))
    z2 = (norm.ppf(1 - ALPHA) + norm.ppf(TARGET_POWER)) ** 2
    task_required = math.ceil(z2 * task_variance / MARGIN**2)

    analytic_grid: list[dict[str, Any]] = []
    required_families = None
    for k in range(2, 2_001):
        df = k - 1
        noncentrality = math.sqrt(k) * MARGIN / max(family_sd, 1e-12)
        power = float(nct.sf(t.ppf(1 - ALPHA, df), df, noncentrality))
        if 24 <= k <= 36:
            analytic_grid.append({"family_count": k, "power_at_true_delta_zero": power})
        if required_families is None and power >= TARGET_POWER:
            required_families = k

    base_counts = np.array(
        [
            [cells["both"], cells["c1_only"], cells["b2_only"], cells["neither"]]
            for _, cells in sorted(family_cells.items())
        ],
        dtype=np.float64,
    )
    pilot_family_size = int(base_counts.sum(axis=1)[0])
    base = base_counts / base_counts.sum(axis=1, keepdims=True)
    shrunk = _shrink_profiles(base, pilot_family_size)
    scenarios: dict[str, tuple[np.ndarray[Any, Any], dict[str, float]]] = {
        "true_delta_zero": _center_profiles(shrunk, 0.0, 1.0),
        "true_delta_zero_heterogeneity_x1_5": _center_profiles(shrunk, 0.0, 1.5),
        "null_margin_boundary": _center_profiles(shrunk, -MARGIN, 1.0),
    }
    rng = np.random.default_rng(SEED)
    simulation: list[dict[str, Any]] = []
    for k in range(24, 37):
        for tasks_per_family in (10, 12, 16, 20):
            if k * tasks_per_family > CEILING:
                continue
            zero = _simulate(scenarios["true_delta_zero"][0], k, tasks_per_family, rng)
            inflated = _simulate(
                scenarios["true_delta_zero_heterogeneity_x1_5"][0],
                k,
                tasks_per_family,
                rng,
            )
            null = _simulate(scenarios["null_margin_boundary"][0], k, tasks_per_family, rng)
            calibration_allowance = CALIBRATION_TOLERANCE + 1.96 * math.sqrt(
                ALPHA * (1 - ALPHA) / REPLICATES
            )
            simulation.append(
                {
                    "family_count": k,
                    "tasks_per_family": tasks_per_family,
                    "total_tasks": k * tasks_per_family,
                    "power_true_delta_zero": zero["rejection_rate"],
                    "power_true_delta_zero_realized_mean": zero["realized_mean_paired_difference"],
                    "power_lower_95_mc": zero["mc_lower_95"],
                    "power_heterogeneity_x1_5": inflated["rejection_rate"],
                    "power_heterogeneity_x1_5_realized_mean": inflated[
                        "realized_mean_paired_difference"
                    ],
                    "inflated_power_lower_95_mc": inflated["mc_lower_95"],
                    "type_i_error_at_margin_boundary": null["rejection_rate"],
                    "type_i_realized_mean_paired_difference": null[
                        "realized_mean_paired_difference"
                    ],
                    "type_i_lower_95_mc": null["mc_lower_95"],
                    "type_i_upper_95_mc": null["mc_upper_95"],
                    "type_i_calibration_compatibility_interval": [
                        ALPHA - calibration_allowance,
                        ALPHA + calibration_allowance,
                    ],
                    "type_i_nominally_compatible": abs(null["rejection_rate"] - ALPHA)
                    <= calibration_allowance,
                    "type_i_controlled": null["rejection_rate"] <= ALPHA + calibration_allowance,
                }
            )

    eligible = [
        row
        for row in simulation
        if row["power_lower_95_mc"] >= TARGET_POWER
        and row["inflated_power_lower_95_mc"] >= TARGET_POWER
        and row["type_i_controlled"]
    ]
    selected = (
        min(eligible, key=lambda row: (row["total_tasks"], row["family_count"]))
        if eligible
        else None
    )
    result = {
        "timestamp_utc": utc_now(),
        "protocol_identity": manifest["protocol_identity"],
        "e07_statistical_identity": E07_IDENTITY,
        "status": "DESIGN_READY" if selected else "INSUFFICIENT_POWER",
        "evidence_class": "Q",
        "task_manifest_sha256": identity,
        "pilot_task_count": len(ids),
        "pilot_family_count": len(family_means),
        "B2_success": sum(row["status"] == "CORRECT" for row in b2_rows),
        "C1_success": sum(row["status"] == "CORRECT" for row in c1_rows),
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
        "primary_test": {
            "null_hypothesis": "mu_D <= -0.05",
            "alternative_hypothesis": "mu_D > -0.05",
            "statistic": "sqrt(K) * (mean(D_j) + 0.05) / sd(D_j)",
            "rejection_rule": "statistic > t_(0.975,K-1)",
            "equal_family_weights": True,
        },
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
            "paired_cell_model": (
                "family empirical four-cell probabilities shrunk toward pooled profile, "
                "then exactly recentered by bounded root solve; whole families resampled"
            ),
            "shrinkage_strength": SHRINKAGE_STRENGTH,
            "heterogeneity_sensitivity_multiplier": 1.5,
            "calibration_absolute_tolerance": CALIBRATION_TOLERANCE,
            "scenario_profile_diagnostics": {
                name: diagnostics for name, (_, diagnostics) in scenarios.items()
            },
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
        "supersedes": "V2-E07-clustered-power / INVALID_CALIBRATION",
        "note": "Qualification planning only. The observed difference is not an efficacy claim.",
    }
    atomic_json(ROOT / "evidence/power_v2/clustered_design_calibrated.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(plan(), indent=2))
