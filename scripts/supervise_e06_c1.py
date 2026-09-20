"""Durable, idempotent C1 resume followed by exact validation and E07."""

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from validate_pilot import validate
from wait_for_gpu_idle import gpu_pids

from contextweave.evidence import ROOT, atomic_json, load_state, save_state, utc_now
from contextweave.power import plan_power

SCRATCH = Path("/home/bjw-0/.cache/contextweave-mcp")
TASK_HASH = "6cfa67f0abd89b954210d68e88f8cdbc9c1cd3bb961c65b899759c89dc21363f"
MODEL_REVISION = "1cfa9a7208912126459214e8b04321603b3df60c"
CHECKPOINT = ROOT / "evidence/pilot/c1_qwen3_4b.jsonl"


def atomic_next_action(message: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=ROOT, delete=False) as f:
        f.write("# Next action\n\n" + message + "\n")
        f.flush()
        os.fsync(f.fileno())
        temp = Path(f.name)
    os.replace(temp, ROOT / "NEXT_ACTION.md")


def checkpoint_count() -> int:
    task_file = ROOT / "benchmarks/pilot_programmatic.jsonl"
    if hashlib.sha256(task_file.read_bytes()).hexdigest() != TASK_HASH:
        raise RuntimeError("frozen pilot task file changed")
    ids = [
        json.loads(line)["task_id"]
        for line in task_file.read_text(encoding="utf-8").splitlines()
        if line
    ]
    rows = (
        [json.loads(line) for line in CHECKPOINT.read_text(encoding="utf-8").splitlines() if line]
        if CHECKPOINT.exists()
        else []
    )
    if len(ids) != 360 or [row["task_id"] for row in rows] != ids[: len(rows)]:
        raise RuntimeError("C1 checkpoint is incomplete, out of task order, or changed")
    if any(
        row["task_manifest_sha256"] != TASK_HASH
        or row["model_revision"] != MODEL_REVISION
        or row["method"] != "C1"
        or row["device"] != "cuda"
        or row["batch_size"] != 4
        for row in rows
    ):
        raise RuntimeError("C1 checkpoint task, model, method, device, or batch changed")
    return len(rows)


def wait_for_exclusive_gpu(seconds: int = 120) -> None:
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
            print(f"GPU idle for {seconds} seconds", flush=True)
            return
        time.sleep(10)


def set_active(count: int, log: Path) -> None:
    state = load_state()
    state["active_long_running_process"] = {
        "kind": "E06-C1-corrected-v3-CUDA-supervised-resume",
        "checkpoint": "evidence/pilot/c1_qwen3_4b.jsonl",
        "completed_rows": count,
        "log": str(log),
        "owner": "one local Qwen3-4B CUDA process; batch size 4; compute owner checked before each batch",
        "started_at_utc": utc_now(),
        "task_manifest_sha256": TASK_HASH,
    }
    state["next_legal_action"] = (
        "Finish supervised corrected-v3 C1, validate all 360 paired tasks, and execute E07 before any design freeze."
    )
    save_state(state)
    atomic_next_action(
        f"Supervised E06 C1 is active from {count}/360 validated rows on frozen task manifest `{TASK_HASH}`. "
        "If interrupted, verify the GPU owner is dead and resume from the atomic checkpoint. "
        "Validate C1 and run E07 before any DESIGN_FREEZE or E08."
    )


def clear_active() -> None:
    state = load_state()
    state["active_long_running_process"] = None
    save_state(state)


def failure_receipt(log: Path, count: int, guard: bool, exit_code: int) -> None:
    suffix = log.stem.removeprefix("e06_c1_")
    receipt = {
        "experiment_id": f"E06-c1-{suffix}",
        "stage": "E06",
        "status": "BLOCKED_BY_GPU_EXCLUSIVITY_GUARD" if guard else "INTERRUPTED_UNDIAGNOSED",
        "evidence_class": "Q",
        "observed_at_utc": utc_now(),
        "process_exit_code": exit_code,
        "checkpoint_rows": count,
        "checkpoint_sha256": hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest(),
        "task_manifest_sha256": TASK_HASH,
        "log": {"path": str(log), "sha256": hashlib.sha256(log.read_bytes()).hexdigest()},
        "scientific_outcome": None,
    }
    atomic_json(ROOT / f"evidence/receipts/{receipt['experiment_id']}.json", receipt)


def main() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with (SCRATCH / "e06_c1_supervisor.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            count = checkpoint_count()
            if count == 360:
                validation = validate("C1")
                clear_active()
                result = plan_power()
                state = load_state()
                state["next_legal_action"] = (
                    "Audit all pre-freeze requirements before DESIGN_FREEZE or E08."
                    if result["feasible"]
                    else "Preserve E07 INSUFFICIENT_POWER; do not enter DESIGN_FREEZE or E08."
                )
                save_state(state)
                atomic_next_action(
                    f"C1 validated {validation['task_count']} exact paired tasks. E07 status is "
                    f"`{result['status']}` with required locked N `{result['required_locked_n']}`. "
                    + state["next_legal_action"]
                )
                print(json.dumps({"validation": validation, "E07": result}, indent=2), flush=True)
                return
            clear_active()
            atomic_next_action(
                f"C1 has {count}/360 valid rows on frozen task manifest `{TASK_HASH}`. "
                "Waiting for 120 seconds of exclusive GPU availability before resuming."
            )
            wait_for_exclusive_gpu()
            log = SCRATCH / f"e06_c1_supervised_{int(time.time())}.log"
            set_active(count, log)
            env = {
                **os.environ,
                "CONTEXTWEAVE_PILOT_METHOD": "C1",
                "CONTEXTWEAVE_PILOT_BATCH_SIZE": "4",
            }
            with log.open("wb") as output:
                result = subprocess.run(
                    [sys.executable, "-u", "-m", "contextweave.model_pilot"],
                    cwd=ROOT,
                    env=env,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
            new_count = checkpoint_count()
            if result.returncode == 0:
                continue
            tail = log.read_text(encoding="utf-8", errors="replace")[-2000:]
            guard = "GPU compute owners changed" in tail or "expected one GPU owner" in tail
            failure_receipt(log, new_count, guard, result.returncode)
            clear_active()
            if not guard:
                atomic_next_action(
                    f"Supervised C1 stopped after {new_count}/360 rows without a recognized GPU guard. "
                    "Audit the durable log and interruption receipt before retrying."
                )
                raise RuntimeError(f"C1 stopped unexpectedly; inspect {log}")
            print(
                f"GPU ownership changed; retained {new_count}/360 rows and will wait again",
                flush=True,
            )


if __name__ == "__main__":
    main()
