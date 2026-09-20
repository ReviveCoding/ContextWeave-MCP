"""Read-only audit of frozen corrected-v3 pilot gold results and task identities."""

import hashlib
import json

import duckdb

from contextweave.benchmark import normalized_hash
from contextweave.evidence import ROOT, atomic_json, utc_now
from contextweave.security import Claims, scoped_sql


def main() -> None:
    path = ROOT / "benchmarks/pilot_programmatic.jsonl"
    manifest = json.loads((ROOT / "benchmarks/pilot_manifest.json").read_text(encoding="utf-8"))
    identity = hashlib.sha256(path.read_bytes()).hexdigest()
    if identity != manifest["task_file_sha256"]:
        raise RuntimeError("frozen task file hash changed")
    tasks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(tasks) != manifest["task_count"] or len({x["task_id"] for x in tasks}) != len(tasks):
        raise RuntimeError("frozen task count or identities changed")
    warehouse = json.loads((ROOT / "evidence/warehouse/manifest.json").read_text(encoding="utf-8"))
    mismatches = []
    conn = duckdb.connect(
        warehouse["database_path"], read_only=True, config={"enable_external_access": "false"}
    )
    try:
        for task in tasks:
            claims = Claims(
                "gold_audit",
                task["tenant_id"],
                tuple(task["account_ids"]),
                frozenset({"analytics:read"}),
                "gold_audit",
                0,
                2**31,
            )
            result = conn.execute(scoped_sql(task["gold_sql"], claims))
            names = [description[0] for description in result.description]
            if normalized_hash(names, result.fetchall()) != task["gold_result_hash"]:
                mismatches.append(task["task_id"])
    finally:
        conn.close()
    receipt = {
        "timestamp_utc": utc_now(),
        "evidence_class": "Q",
        "task_manifest_sha256": identity,
        "warehouse_sha256": warehouse["database_sha256"],
        "task_count": len(tasks),
        "unique_task_count": len({x["task_id"] for x in tasks}),
        "gold_mismatch_count": len(mismatches),
        "gold_mismatch_task_ids": mismatches,
        "status": "PASS" if not mismatches else "FAIL",
    }
    atomic_json(ROOT / "evidence/pilot/frozen_gold_audit.json", receipt)
    print(json.dumps(receipt, indent=2))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
