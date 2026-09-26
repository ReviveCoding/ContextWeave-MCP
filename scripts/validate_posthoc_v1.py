"""Validate the immutable inputs and deterministic post-hoc v1 artifact set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from posthoc_v1 import BOUNDARY, DATA, FIGURES, REPORTS, ROOT, verify_release


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict[str, Any]:
    canonical = verify_release()
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    if manifest["canonical_inputs"] != canonical:
        raise RuntimeError("canonical input hashes differ from the generated manifest")
    for relative, expected in manifest["artifacts"].items():
        path = ROOT / relative
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError(f"post-hoc artifact hash differs: {relative}")
    expected_files = {
        path.relative_to(ROOT).as_posix()
        for directory in (DATA, REPORTS, FIGURES)
        for path in directory.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    if expected_files != set(manifest["artifacts"]):
        raise RuntimeError("post-hoc manifest file inventory differs")
    for report in REPORTS.glob("*.md"):
        if BOUNDARY not in report.read_text(encoding="utf-8"):
            raise RuntimeError(f"governance boundary missing: {report.name}")
    payload = dict(manifest)
    recorded = payload.pop("manifest_payload_sha256")
    actual = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if actual != recorded:
        raise RuntimeError("manifest payload hash differs")
    return {
        "status": "PASS",
        "canonical_inputs": len(canonical),
        "posthoc_artifacts": len(manifest["artifacts"]),
        "manifest_payload_sha256": recorded,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
