"""Fail closed on release evidence, report, and claim-boundary drift."""

from __future__ import annotations

import hashlib
import json

from generate_release_artifacts import CANONICAL_HASHES, ROOT

REQUIRED_REPORTS = (
    "FINAL_TECHNICAL_REPORT.md",
    "EXECUTIVE_SUMMARY.md",
    "DESKTOP_STUDY.md",
    "DATA_AUDIT.md",
    "METHOD_COMPARISON.md",
    "SECURITY_ASSESSMENT.md",
    "SYSTEMS_ASSESSMENT.md",
    "FAILURE_ANALYSIS.md",
    "CLAIM_LEDGER.md",
    "REPRODUCTION_GUIDE.md",
    "RESUME_EVIDENCE.md",
)
REQUIRED_BOUNDARIES = (
    "V1_PRE_FREEZE_INSUFFICIENT_POWER",
    "SUPERSEDED_INVALID_CALIBRATION",
    "V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED",
    "qualification",
    "protected",
    "efficacy",
)


def main() -> None:
    errors: list[str] = []
    for relative, expected in CANONICAL_HASHES.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"canonical hash changed: {relative}")
    state = json.loads((ROOT / "RUN_STATE.json").read_text(encoding="utf-8"))
    if state["protected_accesses"]:
        errors.append("protected_accesses is not empty")
    if state["freeze_identities"]:
        errors.append("freeze_identities is not empty")
    if state["protocol_status"] not in {
        "V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED",
        "RELEASE_CLOSED_PRE_FREEZE_INSUFFICIENT_POWER",
    }:
        errors.append("unexpected protocol_status")
    for name in REQUIRED_REPORTS:
        path = ROOT / "reports" / name
        if not path.is_file() or path.stat().st_size < 200:
            errors.append(f"missing or empty report: {name}")
    combined = "\n".join(
        (ROOT / "reports" / name).read_text(encoding="utf-8") for name in REQUIRED_REPORTS
    )
    for boundary in REQUIRED_BOUNDARIES:
        if boundary.lower() not in combined.lower():
            errors.append(f"claim boundary absent from report set: {boundary}")
    stages = json.loads((ROOT / "evidence/release/stage_matrix.json").read_text(encoding="utf-8"))
    for row in stages["stages"]:
        number = int(row["stage"][1:])
        if 8 <= number <= 25 and row["status"] != "GATED_NOT_RUN":
            errors.append(f"stage {row['stage']} is not marked GATED_NOT_RUN")
    if state["protocol_status"] == "RELEASE_CLOSED_PRE_FREEZE_INSUFFICIENT_POWER":
        e26 = {row["stage"]: row["status"] for row in stages["stages"]}.get("E26")
        if e26 != "RELEASE_CLOSED":
            errors.append("E26 stage matrix is not release-closed")
        for relative in (
            "evidence/quality/release_environment.json",
            "evidence/quality/release_closure.json",
            "evidence/receipts/E26-release-quality.json",
        ):
            path = ROOT / relative
            if (
                not path.is_file()
                or json.loads(path.read_text(encoding="utf-8"))["status"] != "PASS"
            ):
                errors.append(f"missing or failed release closure artifact: {relative}")
    figures = sorted((ROOT / "figures").glob("F*.svg"))
    if len(figures) != 15:
        errors.append(f"expected 15 release figures, found {len(figures)}")
    result = {"status": "PASS" if not errors else "FAIL", "errors": errors}
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
