"""Governance and determinism tests for post-release diagnostics."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from scripts import posthoc_v1

ROOT = Path(__file__).resolve().parents[1]


def load_master() -> list[dict[str, str]]:
    with (ROOT / "evidence/posthoc_v1/task_master.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def test_parent_release_and_canonical_hashes_are_unchanged() -> None:
    assert (
        subprocess.check_output(
            ["git", "rev-list", "-n", "1", posthoc_v1.TAG], cwd=ROOT, text=True
        ).strip()
        == posthoc_v1.PARENT
    )
    canonical = posthoc_v1.verify_release()
    for relative, expected in posthoc_v1.EXPECTED_SHA256.items():
        assert canonical[relative] == expected
    result = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            posthoc_v1.TAG,
            "--",
            "RUN_STATE.json",
            "NEXT_ACTION.md",
            "evidence/pilot_v2",
            "evidence/power_v2",
            "evidence/receipts",
        ],
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0


def test_paired_task_contract() -> None:
    rows = load_master()
    assert len(rows) == 360
    assert len({row["task_id"] for row in rows}) == 360
    family_sizes = Counter(row["semantic_family"] for row in rows)
    assert Counter(family_sizes.values()) == Counter({12: 30})
    cells = Counter(row["paired_transition"] for row in rows)
    assert cells["C1_ONLY"] == 75
    assert cells["B2_ONLY"] == 28
    assert cells["C1_ONLY"] - cells["B2_ONLY"] == 47
    assert sum(row["b2_correct"] == "True" for row in rows) == 200
    assert sum(row["c1_correct"] == "True" for row in rows) == 247


def test_governance_boundary_and_no_inference() -> None:
    manifest = json.loads((ROOT / "evidence/posthoc_v1/manifest.json").read_text(encoding="utf-8"))
    assert manifest["execution"] == {
        "bootstrap_replicates": 100_000,
        "gpu_used": False,
        "model_inference_run": False,
        "protected_data_read": False,
        "release_artifacts_overwritten": False,
        "retrieval_run": False,
        "run_state_modified": False,
        "seed": posthoc_v1.SEED,
    }
    source = (ROOT / "scripts/posthoc_v1.py").read_text(encoding="utf-8")
    assert "import torch" not in source
    assert "import transformers" not in source
    assert "protected" not in " ".join(manifest["canonical_inputs"]).lower()
    assert all(
        path.startswith(("evidence/posthoc_v1/", "reports/posthoc/", "figures/posthoc/"))
        for path in manifest["artifacts"]
    )
    for report in (ROOT / "reports/posthoc").glob("*.md"):
        assert posthoc_v1.BOUNDARY in report.read_text(encoding="utf-8")


def test_manifest_hashes_validate() -> None:
    manifest: dict[str, Any] = json.loads(
        (ROOT / "evidence/posthoc_v1/manifest.json").read_text(encoding="utf-8")
    )
    for relative, expected in manifest["artifacts"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    payload = dict(manifest)
    expected_payload = payload.pop("manifest_payload_sha256")
    actual_payload = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert actual_payload == expected_payload


def test_generation_is_byte_deterministic() -> None:
    before = json.loads((ROOT / "evidence/posthoc_v1/manifest.json").read_text(encoding="utf-8"))
    after = posthoc_v1.generate()
    assert after["artifacts"] == before["artifacts"]
    assert after["manifest_payload_sha256"] == before["manifest_payload_sha256"]
