"""Independent CPU calibration audit for the v2 family-level NI test."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import nct, t

ROOT = Path(__file__).resolve().parents[1]
MARGIN = 0.05
ALPHA = 0.025
REPLICATES = 100_000
SEED = 2026092501
TOLERANCE = 0.0025


def reject(values: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
    k = values.shape[1]
    means = values.mean(axis=1)
    standard_deviation = values.std(axis=1, ddof=1)
    statistic = np.divide(
        means + MARGIN,
        standard_deviation / math.sqrt(k),
        out=np.where(means + MARGIN > 0, np.inf, -np.inf),
        where=standard_deviation > 0,
    )
    return statistic > t.ppf(1 - ALPHA, k - 1)


def center(
    profiles: np.ndarray[Any, Any], delta: float, multiplier: float = 1.0
) -> np.ndarray[Any, Any]:
    discordance = profiles[:, 1] + profiles[:, 2]
    differences = profiles[:, 1] - profiles[:, 2]
    raw = (differences - differences.mean()) * multiplier
    low, high = -2.0, 2.0
    for _ in range(100):
        shift = (low + high) / 2
        if np.clip(raw + shift, -discordance, discordance).mean() < delta:
            low = shift
        else:
            high = shift
    adjusted_difference = np.clip(raw + (low + high) / 2, -discordance, discordance)
    adjusted = profiles.copy()
    adjusted[:, 1] = (discordance + adjusted_difference) / 2
    adjusted[:, 2] = (discordance - adjusted_difference) / 2
    if not np.allclose(adjusted.sum(axis=1), 1.0, atol=1e-12):
        raise RuntimeError("invalid independently centered profiles")
    if not math.isclose(float(adjusted_difference.mean()), delta, abs_tol=1e-12):
        raise RuntimeError("independent centering missed requested delta")
    return adjusted


def binary_simulation(
    profiles: np.ndarray[Any, Any], delta: float, *, k: int = 30, tasks: int = 12, seed: int
) -> dict[str, Any]:
    adjusted = center(profiles, delta)
    rng = np.random.default_rng(seed)
    rejection_count = 0
    realized_sum = 0.0
    for start in range(0, REPLICATES, 5_000):
        size = min(5_000, REPLICATES - start)
        indices = rng.integers(0, len(adjusted), size=(size, k))
        counts = rng.multinomial(tasks, adjusted[indices])
        values = (counts[:, :, 1] - counts[:, :, 2]) / tasks
        rejection_count += int(reject(values).sum())
        realized_sum += float(values.mean(axis=1).sum())
    rate = rejection_count / REPLICATES
    standard_error = math.sqrt(rate * (1 - rate) / REPLICATES)
    return {
        "requested_mean_paired_difference": delta,
        "profile_mean_paired_difference": float((adjusted[:, 1] - adjusted[:, 2]).mean()),
        "realized_mean_paired_difference": realized_sum / REPLICATES,
        "rejection_rate": rate,
        "mc_standard_error": standard_error,
        "mc_95_interval": [
            max(0.0, rate - 1.96 * standard_error),
            min(1.0, rate + 1.96 * standard_error),
        ],
    }


def normal_simulation(delta: float, sigma: float, k: int, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    values = rng.normal(delta, sigma, size=(REPLICATES, k))
    rate = float(reject(values).mean())
    standard_error = math.sqrt(rate * (1 - rate) / REPLICATES)
    noncentrality = math.sqrt(k) * (delta + MARGIN) / sigma
    theoretical = float(nct.sf(t.ppf(1 - ALPHA, k - 1), k - 1, noncentrality))
    return {
        "requested_mean_paired_difference": delta,
        "realized_mean_paired_difference": float(values.mean()),
        "empirical_rejection_rate": rate,
        "theoretical_rejection_rate": theoretical,
        "absolute_empirical_theoretical_difference": abs(rate - theoretical),
        "mc_standard_error": standard_error,
        "mc_95_interval": [
            max(0.0, rate - 1.96 * standard_error),
            min(1.0, rate + 1.96 * standard_error),
        ],
    }


def independent_analytic_power(observed: np.ndarray[Any, Any]) -> dict[str, Any]:
    """Recompute the family-t planning curve without importing project power code."""
    family_differences = observed[:, 1] - observed[:, 2]
    sigma = float(family_differences.std(ddof=1))
    grid: list[dict[str, float | int]] = []
    required_family_count = None
    for k in range(2, 2_001):
        critical = t.ppf(1 - ALPHA, k - 1)
        noncentrality = math.sqrt(k) * MARGIN / sigma
        power = float(nct.sf(critical, k - 1, noncentrality))
        if 24 <= k <= 36:
            grid.append({"family_count": k, "power_at_true_delta_zero": power})
        if required_family_count is None and power >= 0.90:
            required_family_count = k
    return {
        "observed_between_family_sd": sigma,
        "planning_true_difference": 0.0,
        "required_family_count_for_0_90_power": required_family_count,
        "grid_24_to_36": grid,
    }


def old_generator_checkpoint(base: np.ndarray[Any, Any]) -> dict[str, Any]:
    discordance = base[:, 1] + base[:, 2]
    differences = base[:, 1] - base[:, 2]
    shifted = np.clip(differences - differences.mean() - MARGIN, -discordance, discordance)
    adjusted = base.copy()
    adjusted[:, 1] = (discordance + shifted) / 2
    adjusted[:, 2] = (discordance - shifted) / 2
    concentration = 16
    expected_after_dirichlet = adjusted * concentration + 0.5
    expected_after_dirichlet /= expected_after_dirichlet.sum(axis=1, keepdims=True)
    rng = np.random.default_rng(SEED + 99)
    rejected = 0
    realized_sum = 0.0
    for start in range(0, REPLICATES, 5_000):
        size = min(5_000, REPLICATES - start)
        indices = rng.integers(0, len(adjusted), size=(size, 30))
        alpha = adjusted[indices] * concentration + 0.5
        gamma = rng.gamma(alpha, 1.0)
        probabilities = gamma / gamma.sum(axis=2, keepdims=True)
        counts = rng.multinomial(12, probabilities)
        values = (counts[:, :, 1] - counts[:, :, 2]) / 12
        rejected += int(reject(values).sum())
        realized_sum += float(values.mean(axis=1).sum())
    return {
        "requested_null_boundary": -MARGIN,
        "mean_after_clipping": float(shifted.mean()),
        "expected_mean_after_dirichlet_pseudocounts": float(
            (expected_after_dirichlet[:, 1] - expected_after_dirichlet[:, 2]).mean()
        ),
        "realized_mean_paired_difference": realized_sum / REPLICATES,
        "rejection_rate": rejected / REPLICATES,
    }


def observed_profiles() -> np.ndarray[Any, Any]:
    tasks = [
        json.loads(line)
        for line in (ROOT / "benchmarks/v2_pilot_tasks.jsonl").read_text().splitlines()
    ]
    b2 = {
        row["task_id"]: row
        for row in (
            json.loads(line)
            for line in (ROOT / "evidence/pilot_v2/b2_qwen3_4b.jsonl").read_text().splitlines()
        )
    }
    c1 = {
        row["task_id"]: row
        for row in (
            json.loads(line)
            for line in (ROOT / "evidence/pilot_v2/c1_qwen3_4b.jsonl").read_text().splitlines()
        )
    }
    cells: dict[str, Counter[str]] = defaultdict(Counter)
    for task in tasks:
        task_id = task["task_id"]
        baseline = b2[task_id]["status"] == "CORRECT"
        candidate = c1[task_id]["status"] == "CORRECT"
        key = (
            "both"
            if baseline and candidate
            else "c1"
            if candidate
            else "b2"
            if baseline
            else "neither"
        )
        cells[task["semantic_family"]][key] += 1
    base = np.array(
        [
            [value["both"], value["c1"], value["b2"], value["neither"]]
            for _, value in sorted(cells.items())
        ],
        dtype=float,
    )
    return base / base.sum(axis=1, keepdims=True)


def main() -> None:
    observed = observed_profiles()
    pooled = observed.mean(axis=0)
    shrunk = (observed * 12 + 2 * pooled) / 14
    homogeneous = np.array([[0.4, 0.15, 0.15, 0.3]], dtype=float)
    binary = {
        "homogeneous_inferior": binary_simulation(homogeneous, -0.10, seed=SEED + 1),
        "homogeneous_null_boundary": binary_simulation(homogeneous, -0.05, seed=SEED + 2),
        "homogeneous_equal_quality": binary_simulation(homogeneous, 0.0, seed=SEED + 3),
        "homogeneous_strong_positive": binary_simulation(homogeneous, 0.15, seed=SEED + 4),
        "heterogeneous_null_boundary": binary_simulation(shrunk, -0.05, seed=SEED + 5),
        "heterogeneous_equal_quality": binary_simulation(shrunk, 0.0, seed=SEED + 6),
    }
    normal = {
        "null_boundary": normal_simulation(-0.05, 0.2, 30, SEED + 10),
        "equal_quality": normal_simulation(0.0, 0.2, 30, SEED + 11),
        "strong_positive": normal_simulation(0.15, 0.2, 30, SEED + 12),
    }
    nominal_checks = [
        binary["homogeneous_null_boundary"],
        normal["null_boundary"],
    ]
    heterogeneous_stress = binary["heterogeneous_null_boundary"]
    calibration_allowance = TOLERANCE + 1.96 * math.sqrt(ALPHA * (1 - ALPHA) / REPLICATES)
    calibration_interval = [ALPHA - calibration_allowance, ALPHA + calibration_allowance]
    nominally_calibrated = all(
        abs(check.get("rejection_rate", check.get("empirical_rejection_rate")) - ALPHA)
        <= calibration_allowance
        for check in nominal_checks
    )
    heterogeneous_type_i_controlled = (
        heterogeneous_stress["rejection_rate"] <= calibration_interval[1]
    )
    calibrated = nominally_calibrated and heterogeneous_type_i_controlled
    result = {
        "audit_identity": "ContextWeave-v2-E07-calibration-audit-independent-v1",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": "PASS_CONTROLLED_CONSERVATIVE_HETEROGENEITY" if calibrated else "FAIL",
        "replicates_per_checkpoint": REPLICATES,
        "seed": SEED,
        "one_sided_alpha": ALPHA,
        "noninferiority_margin": MARGIN,
        "calibration_absolute_tolerance": TOLERANCE,
        "calibration_compatibility_interval": calibration_interval,
        "calibration_gate": {
            "nominal_reference_and_homogeneous_compatible": nominally_calibrated,
            "heterogeneous_observed_profile_type_i_controlled": heterogeneous_type_i_controlled,
            "heterogeneous_observed_profile_nominally_compatible": abs(
                heterogeneous_stress["rejection_rate"] - ALPHA
            )
            <= calibration_allowance,
            "interpretation": (
                "The normal-reference and homogeneous binary checkpoints must be compatible "
                "with nominal alpha. The observed-profile heterogeneous stress check may be "
                "conservative but must not exceed the upper safety limit."
            ),
        },
        "test_derivation": {
            "null": "mu_D <= -0.05",
            "alternative": "mu_D > -0.05",
            "standard_error": "sd(D_j) / sqrt(K)",
            "statistic": "sqrt(K) * (mean(D_j) + 0.05) / sd(D_j)",
            "critical_value": "t_(0.975,K-1)",
            "rejection_rule": "statistic > critical value",
            "degrees_of_freedom": "K-1",
            "equal_family_weights": True,
        },
        "old_generator_reproduction": old_generator_checkpoint(observed),
        "independent_analytic_power": independent_analytic_power(observed),
        "independent_binary_checkpoints": binary,
        "independent_normal_t_benchmarks": normal,
        "input_hashes": {
            "B2": hashlib.sha256(
                (ROOT / "evidence/pilot_v2/b2_qwen3_4b.jsonl").read_bytes()
            ).hexdigest(),
            "C1": hashlib.sha256(
                (ROOT / "evidence/pilot_v2/c1_qwen3_4b.jsonl").read_bytes()
            ).hexdigest(),
        },
        "protected_accesses": [],
    }
    path = ROOT / "evidence/power_v2/calibration_audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not calibrated:
        raise RuntimeError("independent v2 E07 calibration failed")


if __name__ == "__main__":
    main()
