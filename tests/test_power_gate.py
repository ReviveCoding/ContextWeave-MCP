"""E07 must reject an incomplete paired pilot before writing an outcome."""

import hashlib
import json

import pytest

from contextweave import power


def test_e07_rejects_incomplete_c1(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(power, "ROOT", tmp_path)
    task_dir = tmp_path / "benchmarks"
    pilot_dir = tmp_path / "evidence/pilot"
    task_dir.mkdir()
    pilot_dir.mkdir(parents=True)
    task_file = task_dir / "pilot_programmatic.jsonl"
    task_file.write_text(
        json.dumps({"task_id": "a"}) + "\n" + json.dumps({"task_id": "b"}) + "\n",
        encoding="utf-8",
    )
    (task_dir / "pilot_manifest.json").write_text(
        json.dumps(
            {
                "task_count": 2,
                "task_file_sha256": hashlib.sha256(task_file.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    (pilot_dir / "b2_qwen3_4b.jsonl").write_text(
        json.dumps({"task_id": "a", "method": "B2"})
        + "\n"
        + json.dumps({"task_id": "b", "method": "B2"})
        + "\n",
        encoding="utf-8",
    )
    (pilot_dir / "c1_qwen3_4b.jsonl").write_text(
        json.dumps({"task_id": "a", "method": "C1"}) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="paired pilot outcomes incomplete"):
        power.plan_power()
    assert not (tmp_path / "evidence/power/paired_design.json").exists()
