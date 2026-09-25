"""Regression tests for conservative GPU telemetry and v2 supervisor guards."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import supervise_v2_pilot as supervisor
from wait_for_gpu_idle import GpuSnapshot, query_gpu_state, wait_for_verified_idle

from contextweave.v2_model_pilot import _resume_partition


def completed(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["nvidia-smi"], returncode, stdout, stderr)


def test_nvidia_smi_exit_255_is_unknown() -> None:
    snapshot = query_gpu_state(lambda *args, **kwargs: completed(255, stderr="NVML unavailable"))
    assert snapshot.status == "GPU_STATE_UNKNOWN"
    assert snapshot.owners == frozenset()
    assert snapshot.returncode == 255


def test_empty_successful_owner_list_is_verified_idle() -> None:
    snapshot = query_gpu_state(lambda *args, **kwargs: completed(0, stdout=""))
    assert snapshot.status == "KNOWN"
    assert snapshot.owners == frozenset()


def test_unknown_process_name_with_numeric_pid_is_still_busy() -> None:
    snapshot = query_gpu_state(lambda *args, **kwargs: completed(0, stdout="87028, [Not Found]\n"))
    assert snapshot.status == "KNOWN"
    assert snapshot.owners == frozenset({87028})


def test_known_external_owner_is_busy() -> None:
    snapshot = query_gpu_state(lambda *args, **kwargs: completed(0, stdout="42, python\n"))
    assert snapshot.status == "KNOWN"
    assert snapshot.owners == frozenset({42})


def test_unparseable_owner_is_unknown() -> None:
    snapshot = query_gpu_state(lambda *args, **kwargs: completed(0, stdout="[Not Found], python\n"))
    assert snapshot.status == "GPU_STATE_UNKNOWN"


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def sequenced(values: list[GpuSnapshot]):
    iterator = iter(values)
    last = values[-1]

    def query() -> GpuSnapshot:
        nonlocal last
        try:
            last = next(iterator)
        except StopIteration:
            pass
        return last

    return query


def known(*owners: int) -> GpuSnapshot:
    return GpuSnapshot("KNOWN", frozenset(owners), 0, "", "")


def unknown() -> GpuSnapshot:
    return GpuSnapshot("GPU_STATE_UNKNOWN", frozenset(), 255, "", "NVML unavailable")


def test_transient_unknown_recovers_and_resets_continuous_idle_timer() -> None:
    fake = FakeTime()
    messages: list[str] = []
    wait_for_verified_idle(
        idle_seconds=2,
        poll_seconds=1,
        max_wait_seconds=20,
        query=sequenced([known(), unknown(), known(), known(), known()]),
        sleep=fake.sleep,
        clock=fake.clock,
        log=messages.append,
    )
    assert fake.now == 4
    assert any("GPU_STATE_UNKNOWN returncode=255" in message for message in messages)
    assert messages[-1] == "GPU verified idle for 2 seconds"


def test_changing_owner_pid_resets_idle_timer() -> None:
    fake = FakeTime()
    wait_for_verified_idle(
        idle_seconds=2,
        poll_seconds=1,
        max_wait_seconds=20,
        query=sequenced([known(), known(41), known(42), known(), known(), known()]),
        sleep=fake.sleep,
        clock=fake.clock,
        log=lambda _message: None,
    )
    assert fake.now == 5


def test_supervisor_lock_rejects_duplicate(tmp_path: Path) -> None:
    lock_path = tmp_path / "supervisor.lock"
    with (
        supervisor._supervisor_lock(lock_path),
        pytest.raises(BlockingIOError),
        supervisor._supervisor_lock(lock_path),
    ):
        pass


def test_completed_method_is_not_scheduled_for_duplicate_inference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_path = tmp_path / "tasks.jsonl"
    out_path = tmp_path / "b2.jsonl"
    tasks = [{"task_id": f"task-{index:03d}"} for index in range(360)]
    task_path.write_text("".join(json.dumps(row) + "\n" for row in tasks), encoding="utf-8")
    identity = __import__("hashlib").sha256(task_path.read_bytes()).hexdigest()
    rows = [
        {
            "task_id": task["task_id"],
            "method": "B2",
            "protocol_identity": supervisor.PROTOCOL,
            "task_manifest_sha256": identity,
        }
        for task in tasks
    ]
    out_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    monkeypatch.setattr(supervisor, "TASK_PATH", task_path)
    assert supervisor._method_complete(out_path, "B2")
    rows[-1] = rows[-2]
    out_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    assert not supervisor._method_complete(out_path, "B2")


def test_completed_method_reuses_canonical_validation_without_rewriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path
    pilot = root / "evidence/pilot_v2"
    receipts = root / "evidence/receipts"
    pilot.mkdir(parents=True)
    receipts.mkdir(parents=True)
    task_path = root / "tasks.jsonl"
    out_path = pilot / "b2_qwen3_4b.jsonl"
    task_path.write_text('{"task_id":"one"}\n', encoding="utf-8")
    out_path.write_text('{"task_id":"one"}\n', encoding="utf-8")
    identity = __import__("hashlib").sha256(task_path.read_bytes()).hexdigest()
    outcome_sha = __import__("hashlib").sha256(out_path.read_bytes()).hexdigest()
    validation = {
        "status": "PASS",
        "errors": [],
        "method": "B2",
        "protocol_identity": supervisor.PROTOCOL,
        "task_manifest_sha256": identity,
        "outcome_sha256": outcome_sha,
        "model_revision": supervisor.QWEN_REVISION,
        "device": "cuda",
        "dtype": "bfloat16",
        "batch_size": 4,
        "task_count": 360,
        "unique_task_count": 360,
        "timestamp_utc": "fixed",
    }
    validation_path = pilot / "b2_validation.json"
    validation_path.write_text(json.dumps(validation), encoding="utf-8")
    receipt_path = receipts / "V2-E06-b2-qwen-pilot.json"
    receipt_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "protocol_identity": supervisor.PROTOCOL,
                "task_manifest_sha256": identity,
                "output_manifest": [
                    {
                        "path": "evidence/pilot_v2/b2_qwen3_4b.jsonl",
                        "sha256": outcome_sha,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    before = (validation_path.read_bytes(), receipt_path.read_bytes())
    monkeypatch.setattr(supervisor, "ROOT", root)
    monkeypatch.setattr(supervisor, "TASK_PATH", task_path)
    assert supervisor._load_completed_validation(out_path, "B2") == validation
    assert before == (validation_path.read_bytes(), receipt_path.read_bytes())


def test_partial_c1_resume_excludes_completed_task_ids() -> None:
    tasks = [{"task_id": f"task-{index}"} for index in range(8)]
    existing = {task["task_id"]: {"task_id": task["task_id"], "method": "C1"} for task in tasks[:5]}
    completed_rows, remaining_tasks = _resume_partition(tasks, existing)
    assert [row["task_id"] for row in completed_rows] == [f"task-{index}" for index in range(5)]
    assert [task["task_id"] for task in remaining_tasks] == [
        "task-5",
        "task-6",
        "task-7",
    ]
