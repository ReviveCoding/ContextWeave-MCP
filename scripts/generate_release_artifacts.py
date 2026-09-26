"""Generate release-only figures and stage metadata from canonical evidence."""

from __future__ import annotations

import hashlib
import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
RELEASE = ROOT / "evidence/release"

CANONICAL_HASHES = {
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
    "evidence/receipts/V2-E07-calibrated-clustered-power.json": (
        "171637556422db4d4d6f1652d0537eff7fe55cf9eab96ff4895852728ec12f71"
    ),
    "evidence/receipts/V2-pre-freeze-closure-calibrated.json": (
        "d9cb86d34e1562e9c502316f616939b68348d7a2a1c1e746c9dbbb1ee3adf771"
    ),
}


def load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def svg(title: str, subtitle: str, lines: list[str], *, accent: str = "#2563eb") -> str:
    height = 170 + 34 * len(lines)
    escaped = [html.escape(line) for line in lines]
    rows = "\n".join(
        f'<text x="48" y="{145 + index * 34}" class="body">{line}</text>'
        for index, line in enumerate(escaped)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}">
<style>.title{{font:700 30px system-ui;fill:#0f172a}}.sub{{font:18px system-ui;fill:#475569}}.body{{font:19px ui-monospace,monospace;fill:#1e293b}}.foot{{font:14px system-ui;fill:#64748b}}</style>
<rect width="1200" height="{height}" fill="#f8fafc"/><rect width="16" height="{height}" fill="{accent}"/>
<text x="48" y="54" class="title">{html.escape(title)}</text>
<text x="48" y="88" class="sub">{html.escape(subtitle)}</text>{rows}
<text x="48" y="{height - 24}" class="foot">Generated from canonical repository evidence; qualification is not confirmatory efficacy.</text>
</svg>\n"""


def write_svg(name: str, title: str, subtitle: str, lines: list[str], accent: str) -> None:
    (FIGURES / name).write_text(svg(title, subtitle, lines, accent=accent), encoding="utf-8")


def main() -> None:
    FIGURES.mkdir(exist_ok=True)
    RELEASE.mkdir(parents=True, exist_ok=True)
    actual = {path: sha256(ROOT / path) for path in CANONICAL_HASHES}
    mismatches = {
        path: {"expected": CANONICAL_HASHES[path], "actual": value}
        for path, value in actual.items()
        if value != CANONICAL_HASHES[path]
    }
    if mismatches:
        raise RuntimeError(f"canonical scientific evidence changed: {mismatches}")

    b2 = load("evidence/pilot_v2/b2_summary.json")
    c1 = load("evidence/pilot_v2/c1_summary.json")
    design = load("evidence/power_v2/clustered_design_calibrated.json")
    calibration = load("evidence/power_v2/calibration_audit.json")
    warehouse = load("evidence/warehouse/manifest.json")
    catalog = load("evidence/catalog/audit.json")
    state = load("RUN_STATE.json")
    if state["protected_accesses"] or state["freeze_identities"]:
        raise RuntimeError("release generator refuses protected access or a freeze identity")

    stages = [
        {"stage": f"E{index:02d}", "status": "COMPLETED" if index <= 6 else "GATED_NOT_RUN"}
        for index in range(25)
    ]
    stages[7]["status"] = "CLOSED_INSUFFICIENT_POWER"
    release_status = (
        "RELEASE_CLOSED"
        if state.get("protocol_status") == "RELEASE_CLOSED_PRE_FREEZE_INSUFFICIENT_POWER"
        else "RELEASE_CLOSURE_IN_PROGRESS"
    )
    stages.extend(
        [
            {"stage": "E25", "status": "GATED_NOT_RUN"},
            {"stage": "E26", "status": release_status},
        ]
    )
    atomic_json(
        RELEASE / "stage_matrix.json",
        {
            "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "closure_identity": "V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED",
            "stages": stages,
            "protected_accesses": [],
            "freeze_identities": {},
            "note": "E08-E25 were not run because E07 failed the prespecified power gate.",
        },
    )
    atomic_json(
        RELEASE / "canonical_hashes.json",
        {
            "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "status": "PASS",
            "artifacts": actual,
        },
    )

    write_svg(
        "F01_system_architecture.svg",
        "F1 — Implemented qualification architecture",
        "Local, single-GPU research system",
        [
            "public T1 + controlled T3 → DuckDB warehouse",
            "catalog + dependency graph → retrieval/context planning",
            "BGE-M3 + reranker → frozen rankings",
            "one CUDA Qwen3-4B owner → atomic qualification outcomes",
            "receipts + hashes → governed evidence",
        ],
        "#2563eb",
    )
    write_svg(
        "F02_evidence_domains.svg",
        "F2 — Evidence domains and boundaries",
        "Domains remain separate in the claim ledger",
        [
            "T1: real public event structure",
            "T3: controlled enterprise-style warehouse",
            "Q: v1/v2 qualification outcomes",
            "P / locked / protected: NOT CREATED",
            "X external transfer: NOT RUN / GATED",
        ],
        "#0f766e",
    )
    write_svg(
        "F03_schema_dependency_graph.svg",
        "F3 — Schema and dependency graph audit",
        "Deterministic E04/E05 evidence",
        [
            f"warehouse tables: {warehouse['table_count']}",
            f"warehouse columns: {warehouse['column_count']}",
            f"catalog metrics: {catalog['metric_count']}",
            f"graph nodes / edges: {catalog['node_count']} / {catalog['edge_count']}",
            f"critical closure audited: {str(catalog['critical_closure_audited']).lower()}",
        ],
        "#7c3aed",
    )
    write_svg(
        "F04_baseline_ladder.svg",
        "F4 — Executed qualification methods",
        "The wider baseline ladder was gated before protected evaluation",
        [
            f"B2 BM25 Top-k: {b2['task_success_count']}/360 ({100 * b2['task_success_rate']:.2f}%)",
            f"C1 ContextWeave-R: {c1['task_success_count']}/360 ({100 * c1['task_success_rate']:.2f}%)",
            "paired difference: +13.06 pp — QUALIFICATION ONLY",
            "B-2/B-1/B0/B1/B3-B7/C2 final comparisons: NOT RUN / GATED",
        ],
        "#ea580c",
    )
    gated = {
        "F05_task_success_vs_tokens.svg": (
            "F5 — Task success vs context tokens",
            "E16/E24 NOT RUN / GATED",
        ),
        "F06_task_success_vs_latency.svg": (
            "F6 — Task success vs p95 latency",
            "E21/E24 NOT RUN / GATED",
        ),
        "F07_token_budget_frontier.svg": ("F7 — Token-budget frontier", "E16 NOT RUN / GATED"),
        "F08_task_complexity_slices.svg": ("F8 — Task-complexity slices", "E25 NOT RUN / GATED"),
        "F09_error_taxonomy.svg": ("F9 — Error taxonomy", "E22/E25 NOT RUN / GATED"),
        "F10_stress_ood_heatmap.svg": ("F10 — Stress/OOD heatmap", "E20 NOT RUN / GATED"),
        "F11_security_gate_matrix.svg": (
            "F11 — Security gate matrix",
            "E19 NOT RUN / GATED; software unit checks are not certification",
        ),
        "F12_cache_frontier.svg": ("F12 — Cache latency/freshness frontier", "E18 NOT RUN / GATED"),
        "F13_ablation.svg": ("F13 — Ablation results", "E22 NOT RUN / GATED"),
        "F14_external_validation.svg": (
            "F14 — External validation",
            "E23 Spider2 evaluation NOT RUN / GATED",
        ),
    }
    for name, (title, status) in gated.items():
        write_svg(
            name,
            title,
            status,
            [
                "No protected benchmark or final method freeze exists.",
                "No numerical result is imputed or fabricated.",
                "See evidence/release/stage_matrix.json.",
            ],
            "#64748b",
        )
    write_svg(
        "F15_final_decision.svg",
        "F15 — Final scientific decision",
        "Pre-freeze qualification program",
        [
            "v1: V1_PRE_FREEZE_INSUFFICIENT_POWER",
            "v2 original E07: SUPERSEDED_INVALID_CALIBRATION",
            f"v2 corrected analytic families required: {design['analytic']['required_family_count']}",
            "best feasible simulated power: 0.1165 (target 0.90)",
            f"calibration: {calibration['status']}",
            "decision: V2_PRE_FREEZE_INSUFFICIENT_POWER_CALIBRATED",
        ],
        "#b91c1c",
    )
    manifest = {path.name: sha256(path) for path in sorted(FIGURES.glob("F*.svg"))}
    atomic_json(RELEASE / "figure_manifest.json", manifest)
    print(json.dumps({"figures": len(manifest), "status": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
