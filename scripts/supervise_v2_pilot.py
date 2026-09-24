"""Durable sequential v2 retrieval, paired pilots, validation, and power gate."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from contextweave.evidence import ROOT, atomic_json, load_state, save_state, utc_now
from contextweave.v2_power import plan
from validate_v2_outcomes import validate
from validate_v2_tasks import validate as validate_tasks
from wait_for_gpu_idle import gpu_pids

SCRATCH = Path("/home/bjw-0/.cache/contextweave-mcp")
PROTOCOL = "ContextWeave-v2-family-diverse-qualification"
TASK_PATH = ROOT / "benchmarks/v2_pilot_tasks.jsonl"


class RetryableGpuInterruption(RuntimeError):
    """The scientific child failed closed because exclusive GPU ownership changed."""


def _next(message: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=ROOT, delete=False) as output:
        output.write("# Next action\n\n" + message + "\n")
        output.flush()
        os.fsync(output.fileno())
        temporary = Path(output.name)
    os.replace(temporary, ROOT / "NEXT_ACTION.md")


def _set_active(kind: str, log: Path, method: str | None = None) -> None:
    state = load_state()
    identity = hashlib.sha256(TASK_PATH.read_bytes()).hexdigest()
    state["active_long_running_process"] = {
        "kind": kind,
        "protocol_identity": PROTOCOL,
        "task_manifest_sha256": identity,
        "method": method,
        "log": str(log),
        "started_at_utc": utc_now(),
        "owner": "one local CUDA process; GPU exclusivity checked; no CPU fallback",
    }
    state["next_legal_action"] = f"Complete {kind}; preserve task identity {identity}."
    save_state(state)


def _run(name: str, command: list[str], env: dict[str, str], method: str | None = None) -> None:
    log = SCRATCH / f"v2_{name}.log"
    _set_active(name, log, method)
    with log.open("ab") as output:
        attempt_start = output.tell()
        output.write(f"\nSTART {utc_now()} {' '.join(command)}\n".encode())
        output.flush()
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
        output.write(f"\nEND {utc_now()} exit={result.returncode}\n".encode())
    if result.returncode:
        receipt = {
            "experiment_id": f"V2-{name}-interruption",
            "protocol_identity": PROTOCOL,
            "status": "INTERRUPTED",
            "observed_at_utc": utc_now(),
            "process_exit_code": result.returncode,
            "task_manifest_sha256": hashlib.sha256(TASK_PATH.read_bytes()).hexdigest(),
            "log": {"path": str(log), "sha256": hashlib.sha256(log.read_bytes()).hexdigest()},
            "scientific_outcome": None,
            "evidence_class": "Q",
        }
        atomic_json(ROOT / f"evidence/receipts/{receipt['experiment_id']}.json", receipt)
        state = load_state()
        state["active_long_running_process"] = None
        save_state(state)
        attempt_output = log.read_bytes()[attempt_start:].decode("utf-8", errors="replace")
        if any(
            marker in attempt_output
            for marker in (
                "GPU is not exclusively idle before v2 Qwen load",
                "expected one v2 GPU owner",
                "v2 GPU ownership changed",
            )
        ):
            raise RetryableGpuInterruption(
                f"{name} lost exclusive GPU ownership; checkpoint preserved"
            )
        raise RuntimeError(f"{name} failed; inspect {log}")


def _wait_idle(seconds: int = 120) -> None:
    idle_since = None
    previous: set[int] | None = None
    while True:
        owners = gpu_pids()
        if owners != previous:
            print(f"GPU compute PIDs: {sorted(owners)}", flush=True)
            previous = owners
        if owners:
            idle_since = None
        elif idle_since is None:
            idle_since = time.monotonic()
        elif time.monotonic() - idle_since >= seconds:
            return
        time.sleep(10)


def _receipt(method: str, validation: dict[str, Any]) -> None:
    method_lower = method.lower()
    paths = [
        f"evidence/pilot_v2/{method_lower}_qwen3_4b.jsonl",
        f"evidence/pilot_v2/{method_lower}_summary.json",
        f"evidence/pilot_v2/{method_lower}_validation.json",
    ]
    summary = json.loads((ROOT / paths[1]).read_text())
    receipt = {
        "experiment_id": f"V2-E06-{method_lower}-qwen-pilot",
        "stage": "V2-E06",
        "protocol_identity": PROTOCOL,
        "status": "PASS",
        "evidence_class": "Q",
        "ended_at_utc": utc_now(),
        "task_manifest_sha256": validation["task_manifest_sha256"],
        "model_revision": validation["model_revision"],
        "device_backend": "CUDA/transformers",
        "environment_receipt": {
            "device": summary["device"],
            "dtype": summary["dtype"],
            "batch_size": summary["batch_size"],
            "peak_vram_bytes": summary["peak_vram_bytes"],
        },
        "output_manifest": [
            {
                "path": path,
                "bytes": (ROOT / path).stat().st_size,
                "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
            }
            for path in paths
        ],
    }
    atomic_json(ROOT / f"evidence/receipts/V2-E06-{method_lower}-qwen-pilot.json", receipt)


def main() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with (SCRATCH / "v2_pilot_supervisor.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
        validation_path = ROOT / "evidence/pilot_v2/task_validation.json"
        task_validation = (
            json.loads(validation_path.read_text())
            if validation_path.exists()
            else validate_tasks()
        )
        if (
            task_validation.get("status") != "PASS"
            or task_validation.get("task_manifest_sha256")
            != hashlib.sha256(TASK_PATH.read_bytes()).hexdigest()
        ):
            task_validation = validate_tasks()
        print(json.dumps({"task_validation": task_validation}, indent=2), flush=True)
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        ranking = ROOT / "evidence/retrieval_v2/rankings.jsonl"
        ranking_receipt = ROOT / "evidence/retrieval_v2/rankings_receipt.json"
        if not ranking.exists() or not ranking_receipt.exists():
            _next(
                "V2 tasks validated. Waiting for 120 seconds of exclusive GPU availability for v2 retrieval qualification."
            )
            _wait_idle()
            _run("retrieval", [sys.executable, "-u", "-m", "contextweave.v2_retrieval_eval"], env)
        for method in ("B2", "C1"):
            out = ROOT / f"evidence/pilot_v2/{method.lower()}_qwen3_4b.jsonl"
            complete = (
                out.exists() and sum(1 for line in out.read_text().splitlines() if line) == 360
            )
            if not complete:
                method_env = {
                    **env,
                    "CONTEXTWEAVE_V2_METHOD": method,
                    "CONTEXTWEAVE_V2_BATCH_SIZE": "4",
                }
                while True:
                    _wait_idle(120)
                    try:
                        _run(
                            f"{method.lower()}_qwen",
                            [sys.executable, "-u", "-m", "contextweave.v2_model_pilot"],
                            method_env,
                            method,
                        )
                        break
                    except RetryableGpuInterruption as exc:
                        _next(
                            f"{exc}. Wait for a new continuous exclusive GPU window and resume "
                            "the same atomic checkpoint without recomputing completed task IDs."
                        )
                        print(str(exc), flush=True)
            validation = validate(method)
            _receipt(method, validation)
            print(json.dumps({f"{method}_validation": validation}, indent=2), flush=True)
        result = plan()
        power_path = ROOT / "evidence/power_v2/clustered_design.json"
        atomic_json(
            ROOT / "evidence/receipts/V2-E07-clustered-power.json",
            {
                "experiment_id": "V2-E07-clustered-power",
                "stage": "V2-E07",
                "protocol_identity": PROTOCOL,
                "status": "PASS" if result["status"] == "DESIGN_READY" else "GATED",
                "evidence_class": "Q",
                "ended_at_utc": utc_now(),
                "task_manifest_sha256": result["task_manifest_sha256"],
                "output_manifest": [
                    {
                        "path": "evidence/power_v2/clustered_design.json",
                        "bytes": power_path.stat().st_size,
                        "sha256": hashlib.sha256(power_path.read_bytes()).hexdigest(),
                    }
                ],
                "reason": None
                if result["status"] == "DESIGN_READY"
                else "No 24-36-family design achieved the prespecified analytic and simulation power gate within 600 tasks.",
            },
        )
        state = load_state()
        state["active_long_running_process"] = None
        state["protocol_runs"]["v2"].update(
            {
                "status": result["status"],
                "current_stage": "E07",
                "completed_stages": ["E06"],
                "task_manifest_sha256": result["task_manifest_sha256"],
            }
        )
        state["protocol_status"] = result["status"]
        state["current_stage"] = "V2-E07"
        state["last_valid_checkpoint"] = "V2-E06-c1-qwen-pilot"
        if result["status"] == "DESIGN_READY":
            message = "V2 E07 is DESIGN_READY. Audit all pre-freeze gates, then create new v2 DESIGN_FREEZE and BENCHMARK_FREEZE identities before protected access."
        else:
            message = "V2 E07 is INSUFFICIENT_POWER. Close v2 honestly and proceed to documentation/release without E08-E24 evidence."
        state["next_legal_action"] = message
        save_state(state)
        _next(message)
        print(json.dumps({"V2_E07": result}, indent=2), flush=True)


if __name__ == "__main__":
    main()
