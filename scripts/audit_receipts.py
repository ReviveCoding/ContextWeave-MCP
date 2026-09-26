"""Check receipt output hashes without rewriting historical experiment identities."""

import argparse
import hashlib
import json

from contextweave.evidence import ROOT, atomic_json, utc_now

ARCHIVED_OUTPUTS = {
    (
        "E01-MCP-transports-v3",
        "evidence/mcp/transport_smoke.json",
    ): "evidence/mcp/transport_smoke_v3.json",
}
HISTORICALLY_MUTABLE = {
    ("E00-desktop-study", "sources/registry.json"),
    ("E00-desktop-study", "NEXT_ACTION.md"),
}
PUBLIC_CI_EXCLUDED = {
    (
        "V2-E06-retrieval-qualification",
        "evidence/retrieval_v2/bge_m3_queries.npy",
    ),
}
PORTABLE_TEXT_OUTPUTS = {
    ("V1-pre-freeze-closure", "evidence/protocols/v1_closure.json"),
    ("V2-E06-retrieval-qualification", "evidence/retrieval_v2/validation.json"),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate without rewriting the timestamped receipt-integrity artifact",
    )
    parser.add_argument(
        "--public-ci",
        action="store_true",
        help="allow documented public-checkout exclusions and LF-normalized historical JSON",
    )
    args = parser.parse_args()
    checked = 0
    archived = []
    historical = []
    public_ci_excluded = []
    portable_text_matches = []
    unexplained = []
    for path in sorted((ROOT / "evidence/receipts").glob("*.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        # Closure/state receipts may use a closure identity instead of an experiment ID.
        experiment = receipt.get("experiment_id", receipt.get("closure_identity", path.stem))
        for output in receipt.get("output_manifest", []):
            checked += 1
            rel = output["path"]
            target = ROOT / rel
            actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
            if actual == output["sha256"]:
                continue
            key = (experiment, rel)
            if args.public_ci and key in PUBLIC_CI_EXCLUDED and not target.is_file():
                public_ci_excluded.append(
                    {
                        "experiment_id": experiment,
                        "path": rel,
                        "receipt_sha256": output["sha256"],
                        "reason": "local neural embedding array intentionally excluded from Git",
                    }
                )
                continue
            if args.public_ci and key in PORTABLE_TEXT_OUTPUTS and target.is_file():
                normalized = target.read_bytes().replace(b"\r\n", b"\n")
                receipt_bytes = normalized.replace(b"\n", b"\r\n")
                if hashlib.sha256(receipt_bytes).hexdigest() == output["sha256"]:
                    portable_text_matches.append(
                        {
                            "experiment_id": experiment,
                            "path": rel,
                            "reason": "Git LF content matches historical CRLF receipt bytes",
                        }
                    )
                    continue
            archive_rel = ARCHIVED_OUTPUTS.get(key)
            if archive_rel:
                archive_path = ROOT / archive_rel
                archive_hash = (
                    hashlib.sha256(archive_path.read_bytes()).hexdigest()
                    if archive_path.is_file()
                    else None
                )
                if archive_hash == output["sha256"]:
                    archived.append(
                        {"experiment_id": experiment, "original": rel, "archive": archive_rel}
                    )
                    continue
            if key in HISTORICALLY_MUTABLE:
                historical.append({"experiment_id": experiment, "path": rel})
            else:
                unexplained.append({"experiment_id": experiment, "path": rel})
    result = {
        "timestamp_utc": utc_now(),
        "evidence_class": "Q",
        "receipt_outputs_checked": checked,
        "historical_archives_verified": archived,
        "historically_mutable_outputs_without_snapshot": historical,
        "public_ci_excluded_outputs": public_ci_excluded,
        "portable_text_receipt_matches": portable_text_matches,
        "unexplained_mismatches": unexplained,
        "status": "PASS_WITH_HISTORICAL_CAVEATS" if not unexplained else "FAIL",
    }
    if not args.check_only:
        atomic_json(ROOT / "evidence/quality/receipt_integrity.json", result)
    print(json.dumps(result, indent=2))
    if unexplained:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
