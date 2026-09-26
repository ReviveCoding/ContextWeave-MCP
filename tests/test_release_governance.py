"""Release closure must preserve the pre-freeze scientific boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = {
    "evidence/pilot_v2/b2_qwen3_4b.jsonl": (
        "e1dd2d277f14fa4136109c3df18e79d7241b450d6995c97f21a2d0a45a07ba3f"
    ),
    "evidence/pilot_v2/c1_qwen3_4b.jsonl": (
        "a45de1cd48c8a8b9d6bc7607cf1c71328067d66dca3700ef95e8c0da2abfeb33"
    ),
    "evidence/power_v2/calibration_audit.json": (
        "0f1925dba92669825a97fae53fe0e044db568f790877296ce95b8caabdabbf08"
    ),
    "evidence/power_v2/clustered_design_calibrated.json": (
        "ea5d24011cf4d6bc3caea7d536d9f252123c90c97053c44a68cd29b3854555e1"
    ),
}


def test_canonical_scientific_hashes_are_unchanged() -> None:
    for relative, expected in CANONICAL.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_release_state_has_no_protected_access_or_freeze() -> None:
    state = json.loads((ROOT / "RUN_STATE.json").read_text(encoding="utf-8"))
    assert state["protected_accesses"] == []
    assert state["freeze_identities"] == {}
    assert state["protocol_runs"]["v2"]["closure_identity"] == (
        "V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED"
    )


def test_all_post_e07_scientific_stages_are_gated() -> None:
    matrix = json.loads((ROOT / "evidence/release/stage_matrix.json").read_text(encoding="utf-8"))
    rows = {row["stage"]: row["status"] for row in matrix["stages"]}
    assert all(rows[f"E{index:02d}"] == "GATED_NOT_RUN" for index in range(8, 26))


def test_claim_ledger_blocks_qualification_as_efficacy() -> None:
    ledger = (ROOT / "reports/CLAIM_LEDGER.md").read_text(encoding="utf-8")
    assert "+13.06 percentage-point paired difference is qualification evidence only" in ledger
    assert "no protected task was created or accessed" in ledger
    assert "Unsupported" in ledger
