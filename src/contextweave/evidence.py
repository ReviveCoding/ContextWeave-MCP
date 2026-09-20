"""Durable experiment receipts and conservative stage transitions."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "RUN_STATE.json"
RECEIPT_DIR = ROOT / "evidence" / "receipts"
STAGES = tuple(f"E{i:02d}" for i in range(27))
EVIDENCE_CLASSES = frozenset("PQDEXU")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def source_identity() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if result.returncode == 0:
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=False
        ).stdout
        return result.stdout.strip() + (
            "+dirty:" + hashlib.sha256(dirty.encode()).hexdigest()[:12] if dirty else ""
        )
    paths = sorted((ROOT / "src").rglob("*.py"))
    h = hashlib.sha256()
    for path in paths:
        h.update(path.relative_to(ROOT).as_posix().encode())
        h.update(path.read_bytes())
    return "uncommitted-source-sha256:" + h.hexdigest()


def atomic_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
        temp = Path(f.name)
    os.replace(temp, path)


def load_state() -> dict[str, Any]:
    state: dict[str, Any] = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return state


def save_state(state: dict[str, Any]) -> None:
    state["updated_at_utc"] = utc_now()
    atomic_json(STATE_PATH, state)


def record(
    stage: str,
    experiment_id: str,
    config: dict[str, Any],
    data_models: dict[str, Any],
    environment: dict[str, Any],
    status: str,
    outputs: list[str],
    evidence_class: str,
    start: str,
    reason: str | None = None,
    complete_stage: bool = True,
) -> Path:
    if stage not in STAGES or evidence_class not in EVIDENCE_CLASSES:
        raise ValueError("unknown stage or evidence class")
    if status not in {"PASS", "FAIL", "GATED", "RUNNING"}:
        raise ValueError("unknown receipt status")
    if status == "PASS" and evidence_class == "U":
        raise ValueError("unrun evidence cannot pass")
    manifest = []
    for rel in outputs:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        manifest.append(
            {
                "path": rel,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    receipt = {
        "experiment_id": experiment_id,
        "stage": stage,
        "config_hash": sha256(config),
        "config": config,
        "code_source_identity": source_identity(),
        "data_model_identity": data_models,
        "environment_receipt": environment,
        "device_backend": environment.get("device_backend", "CPU"),
        "started_at_utc": start,
        "ended_at_utc": utc_now(),
        "status": status,
        "reason": reason,
        "output_manifest": manifest,
        "evidence_class": evidence_class,
    }
    path = RECEIPT_DIR / f"{experiment_id}.json"
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous["config_hash"] != receipt["config_hash"]:
            raise ValueError(f"experiment ID reused with different config: {experiment_id}")
        if previous["status"] == "PASS":
            return path
    atomic_json(path, receipt)
    state = load_state()
    if status == "PASS":
        if complete_stage and stage not in state["completed_stages"]:
            state["completed_stages"].append(stage)
        previous = state.get("last_valid_checkpoint")
        previous_stage = previous[:3] if isinstance(previous, str) else ""
        if previous_stage not in STAGES or STAGES.index(stage) >= STAGES.index(previous_stage):
            state["last_valid_checkpoint"] = experiment_id
        if complete_stage:
            state["current_stage"] = next(
                (candidate for candidate in STAGES if candidate not in state["completed_stages"]),
                "E26",
            )
    elif status in {"FAIL", "GATED"}:
        state["failed_or_gated_stages"].append(
            {"stage": stage, "experiment_id": experiment_id, "status": status, "reason": reason}
        )
    save_state(state)
    return path
