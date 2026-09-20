"""Fail-closed completeness and identity check for a corrected-v3 pilot method."""

import argparse
import hashlib
import json

from contextweave.evidence import ROOT, atomic_json, utc_now

QWEN_REVISION = "1cfa9a7208912126459214e8b04321603b3df60c"


def validate(method: str) -> dict[str, object]:
    task_path = ROOT / "benchmarks/pilot_programmatic.jsonl"
    manifest = json.loads((ROOT / "benchmarks/pilot_manifest.json").read_text(encoding="utf-8"))
    identity = hashlib.sha256(task_path.read_bytes()).hexdigest()
    if identity != manifest["task_file_sha256"]:
        raise ValueError("frozen task file changed")
    tasks = [json.loads(line) for line in task_path.read_text(encoding="utf-8").splitlines() if line]
    ids = {task["task_id"] for task in tasks}
    if len(ids) != len(tasks) or len(ids) != manifest["task_count"]:
        raise ValueError("frozen task IDs or task count invalid")
    output = ROOT / f"evidence/pilot/{method.lower()}_qwen3_4b.jsonl"
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line]
    result_ids = [row["task_id"] for row in rows]
    if len(rows) != len(tasks) or len(result_ids) != len(set(result_ids)) or set(result_ids) != ids:
        raise ValueError(f"{method} is incomplete or contains duplicate/unknown task IDs")
    for row in rows:
        if (
            row["task_manifest_sha256"] != identity
            or row["method"] != method
            or row["model_revision"] != QWEN_REVISION
            or row["device"] != "cuda"
            or row["dtype"] != "bfloat16"
            or row["backend"] != "transformers"
        ):
            raise ValueError(f"{method} has a mismatched task, model, or CUDA identity")
    receipt: dict[str, object] = {
        "timestamp_utc": utc_now(),
        "evidence_class": "Q",
        "method": method,
        "status": "PASS",
        "task_count": len(rows),
        "unique_task_count": len(set(result_ids)),
        "task_manifest_sha256": identity,
        "model_revision": QWEN_REVISION,
        "device": "cuda",
        "dtype": "bfloat16",
        "backend": "transformers",
        "outcome_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    atomic_json(ROOT / f"evidence/pilot/{method.lower()}_validation.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("method", choices=["B2", "C1"])
    args = parser.parse_args()
    print(json.dumps(validate(args.method), indent=2))
