"""Validate and record a resumable v2 B2 checkpoint after infrastructure loss."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "ContextWeave-v2-family-diverse-qualification"
TASK_SHA256 = "38cc188a25252a4d7eb981f8a1d24b838aecc83686c24091ccba4c1e1a76ce99"
QWEN_REVISION = "1cfa9a7208912126459214e8b04321603b3df60c"
EXPECTED_ROWS = 196


def sha256(path: Path) -> str:
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


def system_prompt_hash(source_path: Path) -> str:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "SYSTEM_PROMPT" for target in node.targets
        ):
            prompt = ast.literal_eval(node.value)
            return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    raise RuntimeError("SYSTEM_PROMPT not found")


def main() -> None:
    task_path = ROOT / "benchmarks/v2_pilot_tasks.jsonl"
    checkpoint_path = ROOT / "evidence/pilot_v2/b2_qwen3_4b.jsonl"
    source_path = ROOT / "src/contextweave/v2_model_pilot.py"
    if sha256(task_path) != TASK_SHA256:
        raise RuntimeError("frozen v2 task manifest changed")

    raw = checkpoint_path.read_bytes()
    if not raw.endswith(b"\n"):
        raise RuntimeError("B2 checkpoint has a partial/truncated final record")
    tasks = [json.loads(line) for line in task_path.read_text(encoding="utf-8").splitlines() if line]
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
    if len(tasks) != 360 or len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"unexpected task/checkpoint count: {len(tasks)}/{len(rows)}")

    task_ids = [task["task_id"] for task in tasks]
    row_ids = [row["task_id"] for row in rows]
    if len(set(task_ids)) != 360 or len(set(row_ids)) != EXPECTED_ROWS:
        raise RuntimeError("duplicate task or checkpoint ID")
    if row_ids != task_ids[:EXPECTED_ROWS]:
        raise RuntimeError("B2 checkpoint is not the exact ordered manifest prefix")

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
            raise RuntimeError(f"row {index} semantic family changed")
        if row.get("expected_behavior") != task["expected_behavior"]:
            raise RuntimeError(f"row {index} expected behavior changed")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    remaining = task_ids[EXPECTED_ROWS:]
    validation = {
        "artifact": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"),
        "artifact_bytes": len(raw),
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "audit_at_utc": now,
        "checkpoint_rows": len(rows),
        "duplicate_task_ids": [],
        "evidence_class": "Q",
        "expected_total_rows": 360,
        "final_record_complete": True,
        "identity_checks": expected,
        "model_configuration": {
            "chat_template_thinking": False,
            "decoding": "greedy",
            "do_sample": False,
            "max_new_tokens": 160,
            "system_prompt_sha256": system_prompt_hash(source_path),
        },
        "ordered_manifest_prefix": True,
        "protocol_identity": PROTOCOL,
        "remaining_count": len(remaining),
        "remaining_task_ids": remaining,
        "status": "PASS_RESUMABLE",
        "task_manifest_sha256": TASK_SHA256,
        "unique_checkpoint_task_ids": len(set(row_ids)),
    }
    validation_path = ROOT / "evidence/pilot_v2/b2_reboot_validation_196.json"
    atomic_json(validation_path, validation)

    receipt = {
        "checkpoint": {
            "path": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"),
            "rows": len(rows),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "validation_path": str(validation_path.relative_to(ROOT)).replace("\\", "/"),
            "validation_sha256": sha256(validation_path),
        },
        "evidence_class": "Q",
        "experiment_id": "V2-E06-b2-reboot-interruption-20260924",
        "observed_at_utc": now,
        "prior_interruption_receipt": "evidence/receipts/V2-b2_qwen-interruption.json",
        "protocol_identity": PROTOCOL,
        "remaining_rows": len(remaining),
        "scientific_outcome": None,
        "status": "INFRASTRUCTURE_INTERRUPTION",
        "task_manifest_sha256": TASK_SHA256,
    }
    receipt_path = ROOT / "evidence/receipts/V2-E06-b2-reboot-interruption-20260924.json"
    atomic_json(receipt_path, receipt)

    state_path = ROOT / "RUN_STATE.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_long_running_process"] = None
    state["current_stage"] = "V2-E06"
    state["protocol_status"] = "B2_INTERRUPTED_RESUMABLE"
    state["recoverable_checkpoint"] = {
        "method": "B2",
        "path": "evidence/pilot_v2/b2_qwen3_4b.jsonl",
        "rows": len(rows),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "task_manifest_sha256": TASK_SHA256,
        "validation": "evidence/pilot_v2/b2_reboot_validation_196.json",
    }
    v2 = state["protocol_runs"]["v2"]
    v2["current_stage"] = "E06"
    v2["status"] = "B2_INTERRUPTED_RESUMABLE"
    v2["b2_recoverable_rows"] = len(rows)
    v2["b2_recovery_receipt"] = str(receipt_path.relative_to(ROOT)).replace("\\", "/")
    state["next_legal_action"] = (
        "Require 120 continuous seconds of exclusive RTX 4090 availability, then resume v2 B2 "
        f"from {len(rows)}/360 on frozen manifest {TASK_SHA256}; do not recompute completed IDs."
    )
    state["updated_at_utc"] = now
    atomic_json(state_path, state)
    (ROOT / "NEXT_ACTION.md").write_text(
        "# Next action\n\n"
        f"V2 B2 has a validated {len(rows)}/360 atomic checkpoint on `{TASK_SHA256}`. "
        f"The exact {len(remaining)} remaining task IDs are recorded in "
        "`evidence/pilot_v2/b2_reboot_validation_196.json`. Require 120 continuous seconds of "
        "exclusive RTX 4090 availability, relaunch exactly one durable v2 supervisor, and resume "
        "without recomputing completed IDs. Complete paired B2/C1 and clustered E07 before any freeze.\n",
        encoding="utf-8",
    )
    print(json.dumps({"validation": validation_path.as_posix(), "receipt": receipt_path.as_posix()}, indent=2))


if __name__ == "__main__":
    main()
