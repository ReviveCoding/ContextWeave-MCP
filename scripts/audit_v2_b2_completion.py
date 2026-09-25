"""Independently validate completed v2 B2 evidence and reconcile run state."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "ContextWeave-v2-family-diverse-qualification"
TASK_SHA256 = "38cc188a25252a4d7eb981f8a1d24b838aecc83686c24091ccba4c1e1a76ce99"
RESULT_SHA256 = "e1dd2d277f14fa4136109c3df18e79d7241b450d6995c97f21a2d0a45a07ba3f"
QWEN_REVISION = "1cfa9a7208912126459214e8b04321603b3df60c"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as out:
        json.dump(value, out, indent=2, sort_keys=True)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
        temporary = Path(out.name)
    os.replace(temporary, path)


def system_prompt_hash(source: Path) -> str:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "SYSTEM_PROMPT" for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            return hashlib.sha256(value.encode("utf-8")).hexdigest()
    raise RuntimeError("SYSTEM_PROMPT not found")


def main() -> None:
    tasks_path = ROOT / "benchmarks/v2_pilot_tasks.jsonl"
    result_path = ROOT / "evidence/pilot_v2/b2_qwen3_4b.jsonl"
    summary_path = ROOT / "evidence/pilot_v2/b2_summary.json"
    validation_path = ROOT / "evidence/pilot_v2/b2_validation.json"
    receipt_path = ROOT / "evidence/receipts/V2-E06-b2-qwen-pilot.json"
    source_path = ROOT / "src/contextweave/v2_model_pilot.py"

    if digest(tasks_path) != TASK_SHA256:
        raise RuntimeError("frozen v2 task identity changed")
    raw = result_path.read_bytes()
    if not raw.endswith(b"\n") or digest(result_path) != RESULT_SHA256:
        raise RuntimeError("B2 result hash or final-record completeness failed")
    tasks = [
        json.loads(line) for line in tasks_path.read_text(encoding="utf-8").splitlines() if line
    ]
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
    task_ids = [task["task_id"] for task in tasks]
    row_ids = [row["task_id"] for row in rows]
    if len(tasks) != 360 or len(rows) != 360 or row_ids != task_ids:
        raise RuntimeError("B2 rows are incomplete, duplicated, missing, or out of manifest order")
    if len(set(task_ids)) != 360 or len(set(row_ids)) != 360:
        raise RuntimeError("duplicate task IDs")

    expected = {
        "protocol_identity": PROTOCOL,
        "task_manifest_sha256": TASK_SHA256,
        "model_revision": QWEN_REVISION,
        "method": "B2",
        "device": "cuda",
        "backend": "transformers",
        "dtype": "bfloat16",
        "batch_size": 4,
        "context_budget_tokens": 1024,
    }
    task_by_id = {task["task_id"]: task for task in tasks}
    for index, row in enumerate(rows, 1):
        for key, value in expected.items():
            if row.get(key) != value:
                raise RuntimeError(f"row {index} has unexpected {key}: {row.get(key)!r}")
        task = task_by_id[row["task_id"]]
        if row.get("semantic_family") != task["semantic_family"]:
            raise RuntimeError(f"row {index} semantic family mismatch")
        if row.get("expected_behavior") != task["expected_behavior"]:
            raise RuntimeError(f"row {index} expected behavior mismatch")

    successes = sum(row["status"] == "CORRECT" for row in rows)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_expected = {
        "protocol_identity": PROTOCOL,
        "task_manifest_sha256": TASK_SHA256,
        "result_file_sha256": RESULT_SHA256,
        "model_revision": QWEN_REVISION,
        "backend": "transformers",
        "dtype": "bfloat16",
        "device": "NVIDIA GeForce RTX 4090 Laptop GPU",
        "batch_size": 4,
        "task_count": 360,
        "task_success_count": successes,
        "task_success_rate": successes / 360,
    }
    if any(summary.get(key) != value for key, value in summary_expected.items()):
        raise RuntimeError("B2 summary does not match the completed result")

    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation_expected = {
        "status": "PASS",
        "errors": [],
        "method": "B2",
        "protocol_identity": PROTOCOL,
        "task_manifest_sha256": TASK_SHA256,
        "outcome_sha256": RESULT_SHA256,
        "model_revision": QWEN_REVISION,
        "device": "cuda",
        "dtype": "bfloat16",
        "batch_size": 4,
        "task_count": 360,
        "unique_task_count": 360,
    }
    if any(validation.get(key) != value for key, value in validation_expected.items()):
        raise RuntimeError("independent B2 validation is not a matching PASS")

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        receipt.get("experiment_id") != "V2-E06-b2-qwen-pilot"
        or receipt.get("status") != "PASS"
        or receipt.get("protocol_identity") != PROTOCOL
        or receipt.get("task_manifest_sha256") != TASK_SHA256
        or receipt.get("model_revision") != QWEN_REVISION
        or receipt.get("device_backend") != "CUDA/transformers"
    ):
        raise RuntimeError("canonical B2 receipt identity mismatch")
    receipt_outputs = {item["path"]: item for item in receipt.get("output_manifest", [])}
    canonical_paths = [result_path, summary_path, validation_path]
    for path in canonical_paths:
        relative = path.relative_to(ROOT).as_posix()
        item = receipt_outputs.get(relative)
        if (
            item is None
            or item.get("sha256") != digest(path)
            or item.get("bytes") != path.stat().st_size
        ):
            raise RuntimeError(f"canonical B2 receipt output mismatch: {relative}")

    now = datetime.now(UTC).isoformat(timespec="seconds")
    audit = {
        "audit_at_utc": now,
        "decoding_configuration": {
            "chat_template_thinking": False,
            "do_sample": False,
            "max_new_tokens": 160,
            "system_prompt_sha256": system_prompt_hash(source_path),
        },
        "duplicate_task_ids": [],
        "evidence_class": "Q",
        "final_record_complete": True,
        "identity_checks": expected,
        "missing_task_ids": [],
        "ordered_manifest_match": True,
        "protocol_identity": PROTOCOL,
        "receipt_sha256": digest(receipt_path),
        "result_file_bytes": result_path.stat().st_size,
        "result_file_sha256": RESULT_SHA256,
        "status": "PASS_COMPLETE",
        "summary_sha256": digest(summary_path),
        "task_count": 360,
        "task_manifest_sha256": TASK_SHA256,
        "task_success_count": successes,
        "task_success_rate": successes / 360,
        "unique_task_count": 360,
        "validation_sha256": digest(validation_path),
    }
    audit_path = ROOT / "evidence/pilot_v2/b2_completion_audit.json"
    atomic_json(audit_path, audit)

    telemetry_receipt = {
        "classification": "GPU_STATE_UNKNOWN",
        "evidence_class": "Q",
        "experiment_id": "V2-supervisor-gpu-telemetry-interruption-20260924",
        "failed_command": "nvidia-smi --query-compute-apps=pid --format=csv,noheader",
        "observed_at_utc": now,
        "process_exit_code": 255,
        "protocol_identity": PROTOCOL,
        "scientific_outcome": None,
        "status": "INFRASTRUCTURE_INTERRUPTION",
        "task_manifest_sha256": TASK_SHA256,
        "timing": "after canonical B2 completion and before C1 launch",
    }
    telemetry_path = (
        ROOT / "evidence/receipts/V2-supervisor-gpu-telemetry-interruption-20260924.json"
    )
    atomic_json(telemetry_path, telemetry_receipt)

    state_path = ROOT / "RUN_STATE.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    historical = state.setdefault("historical_recovery_checkpoints", [])
    old_checkpoint = state.pop("recoverable_checkpoint", None)
    if old_checkpoint and old_checkpoint not in historical:
        historical.append(old_checkpoint)
    state["active_long_running_process"] = None
    state["last_valid_checkpoint"] = "V2-E06-b2-qwen-pilot"
    state["protocol_status"] = "B2_COMPLETE_C1_PENDING"
    state["current_stage"] = "V2-E06"
    v2 = state["protocol_runs"]["v2"]
    v2.pop("b2_recoverable_rows", None)
    v2["status"] = "B2_COMPLETE_C1_PENDING"
    v2["current_stage"] = "E06"
    v2["b2_result_sha256"] = RESULT_SHA256
    v2["b2_task_count"] = 360
    v2["b2_completion_audit"] = audit_path.relative_to(ROOT).as_posix()
    v2["gpu_telemetry_interruption_receipt"] = telemetry_path.relative_to(ROOT).as_posix()
    checkpoints = v2.setdefault("qualification_checkpoints", [])
    if "V2-E06-b2-qwen-pilot" not in checkpoints:
        checkpoints.append("V2-E06-b2-qwen-pilot")
    state["next_legal_action"] = (
        "Patch and test fail-closed GPU telemetry recovery, require a fresh 120-second verified "
        "exclusive window, then run C1 on the frozen 360-task v2 identity. Do not rerun B2."
    )
    state["updated_at_utc"] = now
    atomic_json(state_path, state)
    (ROOT / "NEXT_ACTION.md").write_text(
        "# Next action\n\nB2 is complete and canonically validated at 360/360 on "
        f"`{TASK_SHA256}` with result SHA-256 `{RESULT_SHA256}`. Patch and test conservative "
        "GPU telemetry recovery, require a fresh 120-second verified-exclusive window, then run "
        "C1 on the identical frozen tasks and inference configuration. Do not rerun B2 and do not "
        "create a freeze before paired validation and v2 E07.\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
