"""Recovery regression tests for stage and checkpoint semantics."""

from pathlib import Path

from contextweave import evidence


def test_auxiliary_receipt_cannot_regress_checkpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    monkeypatch.setattr(evidence, "STATE_PATH", tmp_path / "RUN_STATE.json")
    monkeypatch.setattr(evidence, "RECEIPT_DIR", tmp_path / "evidence/receipts")
    monkeypatch.setattr(evidence, "source_identity", lambda: "test-source")
    (tmp_path / "out.txt").write_text("qualification", encoding="utf-8")
    evidence.atomic_json(
        evidence.STATE_PATH,
        {
            "completed_stages": [f"E{i:02d}" for i in range(6)],
            "current_stage": "E06",
            "last_valid_checkpoint": "E05-catalog-graph-v2",
            "failed_or_gated_stages": [],
        },
    )
    evidence.record("E01", "E01-auxiliary-transport", {}, {}, {}, "PASS", ["out.txt"], "Q", "start")
    state = evidence.load_state()
    assert state["last_valid_checkpoint"] == "E05-catalog-graph-v2"
    assert state["current_stage"] == "E06"
    evidence.record(
        "E06",
        "E06-b2-partial-stage",
        {},
        {},
        {},
        "PASS",
        ["out.txt"],
        "Q",
        "start",
        complete_stage=False,
    )
    state = evidence.load_state()
    assert state["last_valid_checkpoint"] == "E06-b2-partial-stage"
    assert state["current_stage"] == "E06"
    assert state["completed_stages"] == [f"E{i:02d}" for i in range(6)]
