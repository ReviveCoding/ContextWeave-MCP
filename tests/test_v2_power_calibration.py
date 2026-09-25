"""Deterministic calibration tests for the corrected v2 family-level NI design."""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import nct, t

from contextweave.v2_power import ALPHA, MARGIN, _center_profiles, _reject, _simulate


def homogeneous_profiles() -> np.ndarray:
    return np.array([[0.4, 0.15, 0.15, 0.3]], dtype=float)


def heterogeneous_profiles() -> np.ndarray:
    return np.array(
        [
            [0.45, 0.20, 0.05, 0.30],
            [0.35, 0.05, 0.25, 0.35],
            [0.50, 0.10, 0.10, 0.30],
            [0.30, 0.25, 0.15, 0.30],
        ],
        dtype=float,
    )


def test_primary_test_sign_and_boundary() -> None:
    values_above = np.full((1, 30), -MARGIN + 0.01)
    values_above[0, :15] += 0.01
    values_above[0, 15:] -= 0.01
    values_below = values_above - 0.03
    assert _reject(values_above)[0]
    assert not _reject(values_below)[0]


def test_centered_probabilities_are_valid_and_exact() -> None:
    for target in (-0.10, -0.05, 0.0, 0.15):
        adjusted, diagnostics = _center_profiles(heterogeneous_profiles(), target, 1.5)
        assert np.all(adjusted >= 0)
        assert np.allclose(adjusted.sum(axis=1), 1.0)
        assert math.isclose(float((adjusted[:, 1] - adjusted[:, 2]).mean()), target, abs_tol=1e-12)
        assert math.isclose(
            diagnostics["realized_profile_mean_paired_difference"], target, abs_tol=1e-12
        )


def test_homogeneous_binary_calibration_and_ordered_power() -> None:
    rates = {}
    for index, target in enumerate((-0.10, -0.05, 0.0, 0.15)):
        profiles, _ = _center_profiles(homogeneous_profiles(), target, 1.0)
        result = _simulate(
            profiles,
            k=30,
            tasks_per_family=20,
            rng=np.random.default_rng(700 + index),
            replicates=20_000,
        )
        rates[target] = result["rejection_rate"]
        assert abs(result["realized_mean_paired_difference"] - target) < 0.002
    assert rates[-0.10] <= ALPHA
    assert abs(rates[-0.05] - ALPHA) < 0.01
    assert rates[0.0] > rates[-0.05]
    assert rates[0.15] > 0.95


def test_heterogeneous_null_is_calibrated() -> None:
    profiles, _ = _center_profiles(heterogeneous_profiles(), -MARGIN, 1.0)
    result = _simulate(
        profiles,
        k=30,
        tasks_per_family=20,
        rng=np.random.default_rng(801),
        replicates=20_000,
    )
    assert abs(result["realized_mean_paired_difference"] + MARGIN) < 0.002
    assert result["rejection_rate"] <= 0.04


def test_normal_t_benchmark_matches_noncentral_t_power() -> None:
    rng = np.random.default_rng(901)
    replicates = 50_000
    k = 30
    sigma = 0.2
    delta = 0.0
    values = rng.normal(delta, sigma, size=(replicates, k))
    empirical = float(_reject(values).mean())
    noncentrality = math.sqrt(k) * (delta + MARGIN) / sigma
    theoretical = float(nct.sf(t.ppf(1 - ALPHA, k - 1), k - 1, noncentrality))
    assert abs(empirical - theoretical) < 0.01
