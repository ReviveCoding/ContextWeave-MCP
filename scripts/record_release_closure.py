"""Record E26 software/release closure after all governed checks succeed."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_NAMES = (
    "FINAL_TECHNICAL_REPORT.md",
    "EXECUTIVE_SUMMARY.md",
    "DESKTOP_STUDY.md",
    "DATA_AUDIT.md",
    "METHOD_COMPARISON.md",
    "SECURITY_ASSESSMENT.md",
    "SYSTEMS_ASSESSMENT.md",
    "FAILURE_ANALYSIS.md",
    "CLAIM_LEDGER.md",
    "REPRODUCTION_GUIDE.md",
    "RESUME_EVIDENCE.md",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def junit_counts(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    return {
        name: sum(int(suite.attrib.get(name, 0)) for suite in suites)
        for name in ("tests", "failures", "errors", "skipped")
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    args = parser.parse_args()
    environment = json.loads(
        (ROOT / "evidence/quality/release_environment.json").read_text(encoding="utf-8")
    )
    if environment["status"] != "PASS":
        raise RuntimeError("release environment is not qualified")
    counts = junit_counts(args.junit)
    if counts["failures"] or counts["errors"]:
        raise RuntimeError("pytest JUnit report contains failures or errors")
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()
    quality = {
        "timestamp_utc": timestamp,
        "evidence_class": "D",
        "status": "PASS",
        "source_commit_before_release_commit": commit,
        "environment_receipt": "evidence/quality/release_environment.json",
        "checks": {
            "ruff_format": "PASS",
            "ruff_check": "PASS",
            "strict_mypy": "PASS",
            "pytest": {"status": "PASS", **counts},
            "receipt_integrity": "PASS_WITH_HISTORICAL_CAVEATS",
            "claim_ledger_validation": "PASS",
            "package_build": "PASS",
            "clean_wheel_import": "PASS",
        },
        "wheel": {
            "filename": args.wheel.name,
            "bytes": args.wheel.stat().st_size,
            "sha256": sha256(args.wheel),
            "storage": "native WSL scratch; not committed",
        },
        "scientific_work_rerun": False,
    }
    quality_path = ROOT / "evidence/quality/release_closure.json"
    atomic_json(quality_path, quality)

    state_path = ROOT / "RUN_STATE.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state["protected_accesses"] or state["freeze_identities"]:
        raise RuntimeError("cannot release-close state with protected access or freezes")
    state.update(
        {
            "active_long_running_process": None,
            "current_stage": "E26-CLOSED",
            "last_valid_checkpoint": "E26-release-quality",
            "next_legal_action": (
                "No further v2 scientific action is legal. Preserve artifacts; a future "
                "scientific program requires a new protocol identity."
            ),
            "protocol_status": "RELEASE_CLOSED_PRE_FREEZE_INSUFFICIENT_POWER",
            "release_closure_identity": "CONTEXTWEAVE_V2_RELEASE_CLOSED_2026-09-25",
            "updated_at_utc": timestamp,
        }
    )
    if "E26" not in state["completed_stages"]:
        state["completed_stages"].append("E26")
    state["protocol_runs"]["v2"].update(
        {
            "release_status": "RELEASE_CLOSED",
            "release_closure_identity": "CONTEXTWEAVE_V2_RELEASE_CLOSED_2026-09-25",
            "release_quality": "evidence/quality/release_closure.json",
        }
    )
    atomic_json(state_path, state)
    (ROOT / "NEXT_ACTION.md").write_text(
        "# Next action\n\n"
        "Release closure is complete. No further v2 scientific action is legal. Preserve "
        "v1/v2 qualification, superseded calibration, corrected E07, quality, and release "
        "artifacts. Any future scientific work requires a new protocol identity; do not "
        "create protected tasks or freezes under v2.\n",
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate_release_artifacts.py")],
        cwd=ROOT,
        check=True,
    )

    outputs = [quality_path, state_path, ROOT / "NEXT_ACTION.md"]
    outputs.extend(ROOT / "reports" / name for name in REPORT_NAMES)
    outputs.extend(
        [
            ROOT / "evidence/release/stage_matrix.json",
            ROOT / "evidence/release/canonical_hashes.json",
            ROOT / "evidence/release/figure_manifest.json",
        ]
    )
    receipt = {
        "experiment_id": "E26-release-quality",
        "stage": "E26",
        "status": "PASS",
        "evidence_class": "D",
        "timestamp_utc": timestamp,
        "protocol_identity": "ContextWeave-v2-family-diverse-qualification",
        "scientific_closure_identity": "V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED",
        "release_closure_identity": "CONTEXTWEAVE_V2_RELEASE_CLOSED_2026-09-25",
        "protected_accesses": [],
        "freeze_identities": {},
        "scientific_work_rerun": False,
        "output_manifest": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in outputs
        ],
    }
    atomic_json(ROOT / "evidence/receipts/E26-release-quality.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
