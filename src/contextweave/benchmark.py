"""Known-answer pilot task compiler; protected benchmark is frozen separately."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb

from contextweave.evidence import ROOT, atomic_json, canonical_bytes, utc_now
from contextweave.security import Claims, scoped_sql


def normalized_hash(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    # Column labels are not part of result-set equivalence; width and value order are.
    del columns
    normalized = [[round(x, 10) if isinstance(x, float) else x for x in row] for row in rows]
    normalized.sort(key=lambda row: json.dumps(row, sort_keys=True, default=str))
    return hashlib.sha256(canonical_bytes({"rows": normalized})).hexdigest()


def compile_pilot() -> dict[str, Any]:
    warehouse = json.loads((ROOT / "evidence/warehouse/manifest.json").read_text(encoding="utf-8"))
    db_path = Path(warehouse["database_path"])
    conn = duckdb.connect(str(db_path), read_only=True, config={"enable_external_access": "false"})
    campaigns = conn.execute(
        "SELECT campaign_id, tenant_id, account_id, sum(impressions) n "
        "FROM campaign_daily GROUP BY 1,2,3 ORDER BY n DESC LIMIT 60"
    ).fetchall()
    families = [
        (
            "lookup",
            "campaign_identity",
            "What is the name and current status of campaign {c}?",
            "SELECT name,status FROM campaigns WHERE id='{c}'",
            ["campaigns"],
            ["campaigns.id", "campaigns.name", "campaigns.status"],
            [],
        ),
        (
            "aggregation",
            "campaign_volume",
            "How many impressions and clicks did campaign {c} have across the observed period?",
            "SELECT sum(impressions) AS impressions,sum(clicks) AS clicks FROM campaign_daily WHERE campaign_id='{c}'",
            ["campaign_daily"],
            ["campaign_daily.impressions", "campaign_daily.clicks"],
            [],
        ),
        (
            "temporal_comparison",
            "first_week_series",
            "Show daily clicks for campaign {c} for days 0 through 6 in day order.",
            "SELECT day,clicks FROM campaign_daily WHERE campaign_id='{c}' AND day BETWEEN 0 AND 6 ORDER BY day",
            ["campaign_daily"],
            ["campaign_daily.day", "campaign_daily.clicks"],
            [],
        ),
        (
            "metric_reasoning",
            "campaign_ctr",
            "What was the governed CTR for campaign {c} over all observed days?",
            "SELECT sum(clicks)*1.0/nullif(sum(impressions),0) AS ctr FROM campaign_daily WHERE campaign_id='{c}'",
            ["campaign_daily"],
            ["campaign_daily.clicks", "campaign_daily.impressions"],
            ["M_CTR"],
        ),
        (
            "multi_table_join",
            "named_campaign_clicks",
            "Give the campaign name and its total clicks for campaign {c}.",
            "SELECT c.name,sum(d.clicks) AS clicks FROM campaigns c JOIN campaign_daily d ON c.id=d.campaign_id WHERE c.id='{c}' GROUP BY c.name",
            ["campaigns", "campaign_daily"],
            [
                "campaigns.id",
                "campaigns.name",
                "campaign_daily.campaign_id",
                "campaign_daily.clicks",
            ],
            [],
        ),
        (
            "metric_reasoning",
            "attribution_rate",
            "For campaign {c}, how many attributed conversions and what transformed cost per attributed conversion?",
            "SELECT sum(attributed_conversions) AS attributed_conversions,sum(transformed_cost)/nullif(sum(attributed_conversions),0) AS cpa FROM campaign_daily WHERE campaign_id='{c}'",
            ["campaign_daily"],
            ["campaign_daily.attributed_conversions", "campaign_daily.transformed_cost"],
            ["M_ATTR_CONV", "M_CPA"],
        ),
    ]
    tasks = []
    for family, semantic, prompt, sql_template, tables, columns, metrics in families:
        for index, (campaign, tenant, account, _) in enumerate(campaigns):
            sql = sql_template.format(c=campaign)
            claims = Claims(
                "pilot_compiler",
                tenant,
                (account,),
                frozenset({"analytics:read"}),
                "pilot",
                0,
                2**31,
            )
            safe_sql = scoped_sql(sql, claims)
            result = conn.execute(safe_sql)
            names = [description[0] for description in result.description]
            rows = result.fetchall()
            tasks.append(
                {
                    "task_id": f"P-{semantic}-{index:03d}",
                    "source": "programmatic_known_answer",
                    "family": family,
                    "semantic_family": semantic,
                    "difficulty": "medium"
                    if family in {"multi_table_join", "metric_reasoning"}
                    else "easy",
                    "query": prompt.format(c=campaign),
                    "gold_sql": sql,
                    "gold_result_hash": normalized_hash(names, rows),
                    "required_tables": tables,
                    "required_columns": columns,
                    "required_metrics": metrics,
                    "required_docs": [],
                    "expected_behavior": "ANSWER",
                    "tenant_id": tenant,
                    "account_ids": [account],
                    "schema_version": "v1",
                    "metric_version": "v1",
                    "join_depth": 1 if family == "multi_table_join" else 0,
                    "required_table_count": len(tables),
                    "required_column_count": len(columns),
                    "required_metric_count": len(metrics),
                    "graph_distance": 1 if metrics else 0,
                    "ambiguity": 0,
                    "temporal_operations": 1 if family == "temporal_comparison" else 0,
                    "policy_dependencies": 0,
                    "distractor_count": 0,
                }
            )
    conn.close()
    path = ROOT / "benchmarks/pilot_programmatic.jsonl"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        "".join(json.dumps(task, sort_keys=True) + "\n" for task in tasks), encoding="utf-8"
    )
    manifest = {
        "compiled_at_utc": utc_now(),
        "warehouse_sha256": warehouse["database_sha256"],
        "task_count": len(tasks),
        "semantic_families": sorted({task["semantic_family"] for task in tasks}),
        "task_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "evidence_class": "Q",
        "status": "compiled; model pilot not executed",
    }
    atomic_json(ROOT / "benchmarks/pilot_manifest.json", manifest)
    return manifest
