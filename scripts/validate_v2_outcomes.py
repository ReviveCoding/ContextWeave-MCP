"""Validate one completed v2 model outcome checkpoint against frozen identities."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from contextweave.evidence import ROOT, atomic_json, utc_now
from contextweave.model_pilot import QWEN_REVISION


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def validate(method: str) -> dict[str, Any]:
    method = method.upper()
    if method not in {"B2", "C1"}:
        raise ValueError("method must be B2 or C1")
    task_path = ROOT / "benchmarks/v2_pilot_tasks.jsonl"
    manifest = json.loads((ROOT / "benchmarks/v2_pilot_manifest.json").read_text())
    identity = hashlib.sha256(task_path.read_bytes()).hexdigest()
    tasks = _rows(task_path)
    out = ROOT / f"evidence/pilot_v2/{method.lower()}_qwen3_4b.jsonl"
    outcomes = _rows(out)
    errors: list[str] = []
    task_ids = [x["task_id"] for x in tasks]
    outcome_ids = [x["task_id"] for x in outcomes]
    if identity != manifest["task_file_sha256"]:
        errors.append("task identity differs from manifest")
    if outcome_ids != task_ids or len(outcome_ids) != len(set(outcome_ids)):
        errors.append("outcomes are incomplete, duplicated, or out of task order")
    for row in outcomes:
        if (
            row.get("task_manifest_sha256") != identity
            or row.get("protocol_identity") != manifest["protocol_identity"]
            or row.get("method") != method
            or row.get("model_revision") != QWEN_REVISION
            or row.get("device") != "cuda"
            or row.get("dtype") != "bfloat16"
            or row.get("batch_size") != 4
        ):
            errors.append(f"identity/device/config mismatch in {row.get('task_id')}")
            break
    summary_path = ROOT / f"evidence/pilot_v2/{method.lower()}_summary.json"
    summary = json.loads(summary_path.read_text())
    outcome_sha = hashlib.sha256(out.read_bytes()).hexdigest()
    if (
        summary.get("result_file_sha256") != outcome_sha
        or summary.get("task_manifest_sha256") != identity
        or summary.get("task_count") != 360
        or summary.get("batch_size") != 4
    ):
        errors.append("summary identity differs from outcomes")
    result = {
        "timestamp_utc": utc_now(),
        "protocol_identity": manifest["protocol_identity"],
        "method": method,
        "status": "PASS" if not errors else "FAIL",
        "task_count": len(outcomes),
        "unique_task_count": len(set(outcome_ids)),
        "task_manifest_sha256": identity,
        "outcome_sha256": outcome_sha,
        "model_revision": QWEN_REVISION,
        "device": "cuda",
        "dtype": "bfloat16",
        "batch_size": 4,
        "errors": errors,
        "evidence_class": "Q",
    }
    atomic_json(ROOT / f"evidence/pilot_v2/{method.lower()}_validation.json", result)
    if errors:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print(json.dumps(validate(sys.argv[1]), indent=2))
