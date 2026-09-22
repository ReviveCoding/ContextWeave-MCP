"""Mechanical validation for the v2 qualification task identity and gold answers."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import duckdb

from contextweave.benchmark import normalized_hash
from contextweave.evidence import ROOT, atomic_json, utc_now
from contextweave.security import Claims, scoped_sql


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _normalized_template(text: str) -> str:
    text = re.sub(r"\b\d+\b", "<n>", text.casefold())
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", _normalized_template(text)))


def validate() -> dict[str, Any]:
    task_path = ROOT / "benchmarks/v2_pilot_tasks.jsonl"
    manifest_path = ROOT / "benchmarks/v2_pilot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks = _rows(task_path)
    errors: list[str] = []
    task_ids = [task["task_id"] for task in tasks]
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        families[task["semantic_family"]].append(task)
    if len(tasks) != 360 or len(set(task_ids)) != 360:
        errors.append("expected 360 unique task IDs")
    if len(families) != 30 or any(len(items) != 12 for items in families.values()):
        errors.append("expected 30 semantic families with 12 tasks each")
    observed_sha = hashlib.sha256(task_path.read_bytes()).hexdigest()
    if observed_sha != manifest["task_file_sha256"]:
        errors.append("task manifest hash mismatch")
    signatures = {
        family: {x["template_signature"] for x in items} for family, items in families.items()
    }
    signature_owners: dict[str, list[str]] = defaultdict(list)
    for family, values in signatures.items():
        for value in values:
            signature_owners[value].append(family)
    cross_family_signature_collisions = {
        signature: owners for signature, owners in signature_owners.items() if len(owners) > 1
    }
    if cross_family_signature_collisions:
        errors.append("exact normalized template signature reused across semantic families")
    representatives = {family: items[0]["query"] for family, items in families.items()}
    near_pairs: list[dict[str, Any]] = []
    names = sorted(representatives)
    for i, left in enumerate(names):
        left_tokens = _tokens(representatives[left])
        for right in names[i + 1 :]:
            right_tokens = _tokens(representatives[right])
            score = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
            if score >= 0.8:
                near_pairs.append({"left": left, "right": right, "token_jaccard": score})
    if near_pairs:
        errors.append("near-duplicate representative templates across semantic families")
    v1_tasks = _rows(ROOT / "benchmarks/pilot_programmatic.jsonl")
    v1_families = {x["semantic_family"] for x in v1_tasks}
    v1_templates = {_normalized_template(x["query"]) for x in v1_tasks}
    family_overlap = sorted(v1_families & set(families))
    template_overlap = sorted(
        {
            task["semantic_family"]
            for task in tasks
            if _normalized_template(task["query"]) in v1_templates
        }
    )
    if family_overlap or template_overlap:
        errors.append("v1 semantic family or exact normalized template reused")
    warehouse = json.loads((ROOT / "evidence/warehouse/manifest.json").read_text())
    conn = duckdb.connect(
        warehouse["database_path"], read_only=True, config={"enable_external_access": "false"}
    )
    gold_checked = 0
    for task in tasks:
        behavior = task["expected_behavior"]
        if behavior == "ANSWER":
            if not task["gold_sql"] or not task["gold_result_hash"]:
                errors.append(f"{task['task_id']}: ANSWER task lacks gold")
                continue
            claims = Claims(
                "v2_validator",
                task["tenant_id"],
                tuple(task["account_ids"]),
                frozenset({"analytics:read"}),
                "v2",
                0,
                2**31,
            )
            result = conn.execute(scoped_sql(task["gold_sql"], claims))
            columns = [description[0] for description in result.description]
            actual = normalized_hash(columns, result.fetchall())
            gold_checked += 1
            if actual != task["gold_result_hash"]:
                errors.append(f"{task['task_id']}: result hash mismatch")
        elif task["gold_sql"] is not None or task["gold_result_hash"] is not None:
            errors.append(f"{task['task_id']}: behavior task unexpectedly has SQL gold")
        if task["split"] != "v2_qualification" or not task["family_group"].startswith("v2q:"):
            errors.append(f"{task['task_id']}: split/family group invalid")
    conn.close()
    review_path = ROOT / "benchmarks/v2_independent_adversarial_families.json"
    review_sha = hashlib.sha256(review_path.read_bytes()).hexdigest()
    if review_sha != manifest["independent_review_sha256"]:
        errors.append("independent blind-review hash mismatch")
    reviewed = {x["independent_review_family"] for x in tasks if x["independent_review_family"]}
    if len(reviewed) != 8:
        errors.append("all eight blind-reviewed constructs were not integrated")
    result = {
        "timestamp_utc": utc_now(),
        "protocol_identity": manifest["protocol_identity"],
        "status": "PASS" if not errors else "FAIL",
        "task_count": len(tasks),
        "unique_task_count": len(set(task_ids)),
        "family_count": len(families),
        "family_size_distribution": dict(sorted(Counter(map(len, families.values())).items())),
        "gold_sql_checked": gold_checked,
        "behavior_counts": dict(sorted(Counter(x["expected_behavior"] for x in tasks).items())),
        "task_manifest_sha256": observed_sha,
        "v1_family_overlap": family_overlap,
        "v1_exact_template_overlap": template_overlap,
        "cross_family_template_signature_collisions": cross_family_signature_collisions,
        "near_duplicate_representative_pairs": near_pairs,
        "independent_review_sha256": review_sha,
        "independent_reviewed_construct_count": len(reviewed),
        "protected_tasks_constructed": False,
        "errors": errors,
        "evidence_class": "Q",
    }
    atomic_json(ROOT / "evidence/pilot_v2/task_validation.json", result)
    if errors:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
