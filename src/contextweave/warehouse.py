"""Controlled 32-table enterprise extension anchored to Criteo campaign/day aggregates."""

from __future__ import annotations

import json
import os
from typing import Any

import duckdb

from contextweave.data import SCRATCH, file_sha256
from contextweave.evidence import ROOT, atomic_json, load_state, record, save_state, utc_now

BASE = (
    "id VARCHAR PRIMARY KEY",
    "tenant_id VARCHAR",
    "account_id VARCHAR",
    "valid_from BIGINT",
    "valid_until BIGINT",
    "record_version VARCHAR",
    "provenance VARCHAR",
    "is_generated BOOLEAN",
)

CUSTOM: dict[str, tuple[str, ...]] = {
    "accounts": ("name VARCHAR", "status VARCHAR", "currency VARCHAR"),
    "advertisers": ("name VARCHAR", "industry VARCHAR", "parent_account VARCHAR"),
    "campaigns": (
        "advertiser_id VARCHAR",
        "name VARCHAR",
        "status VARCHAR",
        "start_day INTEGER",
        "end_day INTEGER",
    ),
    "ad_groups": ("campaign_id VARCHAR", "name VARCHAR", "status VARCHAR"),
    "ads": ("ad_group_id VARCHAR", "creative_type VARCHAR", "status VARCHAR"),
    "keywords": ("ad_group_id VARCHAR", "keyword_text VARCHAR", "match_type VARCHAR"),
    "audiences": ("name VARCHAR", "segment_type VARCHAR", "estimated_size BIGINT"),
    "products": ("name VARCHAR", "category VARCHAR", "price DOUBLE"),
    "marketplaces": ("name VARCHAR", "region VARCHAR", "currency VARCHAR"),
    "campaign_config": (
        "campaign_id VARCHAR",
        "delivery_state VARCHAR",
        "objective VARCHAR",
        "timezone VARCHAR",
    ),
    "budget_config": (
        "campaign_id VARCHAR",
        "daily_limit DOUBLE",
        "lifetime_limit DOUBLE",
        "pacing VARCHAR",
    ),
    "bid_config": ("campaign_id VARCHAR", "bid_type VARCHAR", "base_bid DOUBLE", "max_bid DOUBLE"),
    "targeting_config": (
        "campaign_id VARCHAR",
        "audience_id VARCHAR",
        "marketplace_id VARCHAR",
        "is_exclusion BOOLEAN",
    ),
    "conversion_config": (
        "campaign_id VARCHAR",
        "attribution_window_days INTEGER",
        "conversion_type VARCHAR",
        "value_source VARCHAR",
    ),
    "impression_events": (
        "campaign_id VARCHAR",
        "uid_hash VARCHAR",
        "event_ts BIGINT",
        "clicked INTEGER",
        "converted INTEGER",
        "attributed INTEGER",
        "transformed_cost DOUBLE",
    ),
    "click_events": (
        "campaign_id VARCHAR",
        "impression_id VARCHAR",
        "event_ts BIGINT",
        "click_position INTEGER",
    ),
    "conversion_events": (
        "campaign_id VARCHAR",
        "impression_id VARCHAR",
        "event_ts BIGINT",
        "attribution_flag INTEGER",
        "synthetic_value DOUBLE",
    ),
    "campaign_daily": (
        "campaign_id VARCHAR",
        "day INTEGER",
        "impressions BIGINT",
        "clicks BIGINT",
        "conversions BIGINT",
        "attributed_conversions BIGINT",
        "transformed_cost DOUBLE",
        "attributed_value DOUBLE",
    ),
    "adgroup_daily": (
        "ad_group_id VARCHAR",
        "day INTEGER",
        "impressions BIGINT",
        "clicks BIGINT",
        "transformed_cost DOUBLE",
    ),
    "keyword_daily": (
        "keyword_id VARCHAR",
        "day INTEGER",
        "impressions BIGINT",
        "clicks BIGINT",
        "transformed_cost DOUBLE",
    ),
    "account_daily": (
        "day INTEGER",
        "impressions BIGINT",
        "clicks BIGINT",
        "conversions BIGINT",
        "transformed_cost DOUBLE",
    ),
    "auction_daily": (
        "marketplace_id VARCHAR",
        "day INTEGER",
        "auctions BIGINT",
        "wins BIGINT",
        "mean_bid DOUBLE",
    ),
    "metric_definitions": (
        "metric_id VARCHAR",
        "canonical_name VARCHAR",
        "formula VARCHAR",
        "unit VARCHAR",
        "grain VARCHAR",
    ),
    "metric_dependencies": ("metric_id VARCHAR", "object_id VARCHAR", "dependency_type VARCHAR"),
    "business_terms": ("term VARCHAR", "definition VARCHAR", "metric_id VARCHAR"),
    "schema_aliases": ("alias VARCHAR", "canonical_object VARCHAR", "schema_version VARCHAR"),
    "budget_policies": ("policy_text VARCHAR", "severity VARCHAR", "campaign_id VARCHAR"),
    "bid_policies": ("policy_text VARCHAR", "severity VARCHAR", "campaign_id VARCHAR"),
    "targeting_policies": ("policy_text VARCHAR", "severity VARCHAR", "audience_id VARCHAR"),
    "account_constraints": (
        "constraint_text VARCHAR",
        "severity VARCHAR",
        "marketplace_id VARCHAR",
    ),
    "schema_versions": ("schema_version VARCHAR", "change_note VARCHAR", "effective_ts BIGINT"),
    "metric_versions": ("metric_id VARCHAR", "metric_version VARCHAR", "effective_ts BIGINT"),
    "data_freshness": ("source_table VARCHAR", "watermark_ts BIGINT", "freshness_sla_sec BIGINT"),
    "permission_scope": ("subject_id VARCHAR", "scope VARCHAR", "revoked BOOLEAN"),
    "audit_events": ("subject_id VARCHAR", "event_type VARCHAR", "event_ts BIGINT"),
    "cache_versions": ("cache_name VARCHAR", "source_version VARCHAR", "watermark_ts BIGINT"),
}


def build_warehouse() -> dict[str, Any]:
    started = utc_now()
    eda_path = ROOT / "evidence/data/criteo_eda.json"
    if not eda_path.exists():
        raise RuntimeError("E03 canonical audit required before warehouse generation")
    eda = json.loads(eda_path.read_text(encoding="utf-8"))
    parquet = SCRATCH / "curated/criteo_events.parquet"
    if file_sha256(parquet) != eda["parquet_sha256"]:
        raise ValueError("T1 curated parquet identity changed")
    path = SCRATCH / "warehouse/contextweave_v2.duckdb"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError("evaluation warehouse already exists; refuse overwrite")
    conn = duckdb.connect(str(path))
    conn.execute("SET memory_limit='8GB'")
    conn.execute(f"SET temp_directory='{SCRATCH / 'duckdb_tmp'}'")
    ddl_lines = []
    for name, columns in CUSTOM.items():
        ddl = f"CREATE TABLE {name} (" + ", ".join((*BASE, *columns)) + ");"
        ddl_lines.append(ddl)
        conn.execute(ddl)
    # Account assignment is deterministic and generated, not a Criteo account label.
    for i in range(20):
        tenant = f"tenant_{i // 5:02d}"
        account = f"account_{i:02d}"
        conn.execute(
            "INSERT INTO accounts (id,tenant_id,account_id,valid_from,record_version,provenance,is_generated,name,status,currency) VALUES (?,?,?,0,'v1','controlled synthetic',true,?,'active','SYN')",
            [account, tenant, account, account],
        )
        conn.execute(
            "INSERT INTO permission_scope (id,tenant_id,account_id,valid_from,record_version,provenance,is_generated,subject_id,scope,revoked) VALUES (?,?,?,0,'v1','controlled synthetic',true,?,'analytics:read',false)",
            [f"perm_{i}", tenant, account, f"analyst_{i}"],
        )
    parquet_sql = str(parquet).replace("'", "''")
    conn.execute(f"CREATE TEMP VIEW raw_events AS SELECT * FROM read_parquet('{parquet_sql}')")
    conn.execute(
        "INSERT INTO campaigns (id,tenant_id,account_id,valid_from,record_version,provenance,is_generated,advertiser_id,name,status,start_day,end_day) "
        "SELECT campaign, 'tenant_' || lpad(cast((hash(campaign)%20)//5 AS VARCHAR),2,'0'), "
        "'account_' || lpad(cast(hash(campaign)%20 AS VARCHAR),2,'0'), 0,'v1','T1 campaign ID; generated tenant/account',true, "
        "'synthetic_advertiser','Campaign ' || campaign,'active',0,30 FROM (SELECT DISTINCT campaign FROM raw_events)"
    )
    conn.execute(
        "INSERT INTO campaign_daily (id,tenant_id,account_id,valid_from,record_version,provenance,is_generated,campaign_id,day,impressions,clicks,conversions,attributed_conversions,transformed_cost,attributed_value) "
        "SELECT campaign || ':' || cast(floor(timestamp/86400) AS INTEGER)::VARCHAR, "
        "'tenant_' || lpad(cast((hash(campaign)%20)//5 AS VARCHAR),2,'0'), "
        "'account_' || lpad(cast(hash(campaign)%20 AS VARCHAR),2,'0'),0,'v1', "
        "'T1 aggregate; attributed_value generated',true,campaign,cast(floor(timestamp/86400) AS INTEGER), "
        "count(*),sum(click),sum(conversion),sum(attribution),sum(cost),sum(attribution)*1.0 "
        "FROM raw_events GROUP BY campaign,cast(floor(timestamp/86400) AS INTEGER)"
    )
    conn.execute(
        "INSERT INTO impression_events (id,tenant_id,account_id,valid_from,record_version,provenance,is_generated,campaign_id,uid_hash,event_ts,clicked,converted,attributed,transformed_cost) "
        "SELECT cast(row_number() over () AS VARCHAR), "
        "'tenant_' || lpad(cast((hash(campaign)%20)//5 AS VARCHAR),2,'0'), "
        "'account_' || lpad(cast(hash(campaign)%20 AS VARCHAR),2,'0'),0,'v1','T1 first 100000 events; generated account',true, "
        "campaign,sha256(uid),timestamp,click,conversion,attribution,cost "
        "FROM (SELECT * FROM raw_events ORDER BY timestamp LIMIT 100000)"
    )
    conn.execute(
        "INSERT INTO click_events (id,tenant_id,account_id,valid_from,record_version,provenance,is_generated,campaign_id,impression_id,event_ts,click_position) "
        "SELECT 'click_' || id,tenant_id,account_id,0,'v2','T1 clicked event subset',true,campaign_id,id,event_ts,0 "
        "FROM impression_events WHERE clicked=1"
    )
    conn.execute(
        "INSERT INTO conversion_events (id,tenant_id,account_id,valid_from,record_version,provenance,is_generated,campaign_id,impression_id,event_ts,attribution_flag,synthetic_value) "
        "SELECT 'conv_' || id,tenant_id,account_id,0,'v2','T1 conversion event subset; value generated',true,campaign_id,id,event_ts,attributed,1.0 "
        "FROM impression_events WHERE converted=1"
    )
    conn.execute(
        "INSERT INTO account_daily (id,tenant_id,account_id,valid_from,record_version,provenance,is_generated,day,impressions,clicks,conversions,transformed_cost) "
        "SELECT account_id || ':' || day,tenant_id,account_id,0,'v2','T1 derived account/day with generated account mapping',true,day, "
        "sum(impressions),sum(clicks),sum(conversions),sum(transformed_cost) FROM campaign_daily GROUP BY tenant_id,account_id,day"
    )
    representatives = {
        account: campaign
        for account, campaign in conn.execute(
            "SELECT account_id,min(id) FROM campaigns GROUP BY account_id"
        ).fetchall()
    }

    def generated_value(column: str, index: int, campaign: str) -> object:
        name, kind = column.split()
        if kind == "BOOLEAN":
            return False
        if kind in {"INTEGER", "BIGINT"}:
            if name == "day":
                return index % 31
            if "watermark" in name:
                return eda["max_ts"]
            if "sla" in name:
                return 86400
            if "timestamp" in name or name.endswith("_ts"):
                return index * 86400
            return 100 + index
        if kind == "DOUBLE":
            return 1.0 + index / 10
        values = {
            "campaign_id": campaign,
            "advertiser_id": f"advertisers_{index}",
            "ad_group_id": f"ad_groups_{index}",
            "audience_id": f"audiences_{index}",
            "marketplace_id": f"marketplaces_{index}",
            "keyword_id": f"keywords_{index}",
            "metric_id": "M_CTR",
            "schema_version": "v2",
            "metric_version": "v1",
            "source_version": eda["parquet_sha256"][:12],
            "source_table": "campaign_daily",
            "scope": "analytics:read",
            "severity": "informational",
            "status": "active",
            "currency": "SYN",
            "formula": "SUM(clicks)/NULLIF(SUM(impressions),0)",
            "unit": "ratio",
            "grain": "campaign-day",
            "policy_text": "Synthetic policy: review daily pacing before budget changes.",
            "constraint_text": "Synthetic constraint: account-scoped analytical access only.",
            "definition": "Controlled synthetic business term.",
            "change_note": "Controlled synthetic schema version.",
        }
        return values.get(name, f"synthetic_{name}_{index}")

    # Every remaining family has account-scoped, explicitly generated non-null content.
    seeded = {
        "accounts",
        "campaigns",
        "campaign_daily",
        "impression_events",
        "click_events",
        "conversion_events",
        "account_daily",
        "permission_scope",
        "metric_definitions",
    }
    for name in sorted(CUSTOM.keys() - seeded):
        custom = CUSTOM[name]
        custom_names = [column.split()[0] for column in custom]
        columns_sql = ",".join(
            [
                "id",
                "tenant_id",
                "account_id",
                "valid_from",
                "record_version",
                "provenance",
                "is_generated",
                *custom_names,
            ]
        )
        placeholders = ",".join("?" for _ in range(7 + len(custom)))
        for i in range(20):
            account = f"account_{i:02d}"
            campaign = representatives[account]
            values = [
                f"{name}_{i}",
                f"tenant_{i // 5:02d}",
                account,
                0,
                "v2",
                "controlled synthetic",
                True,
            ]
            values.extend(generated_value(column, i, campaign) for column in custom)
            conn.execute(f"INSERT INTO {name} ({columns_sql}) VALUES ({placeholders})", values)
    from contextweave.catalog import METRICS

    for metric in METRICS:
        conn.execute(
            "INSERT INTO metric_definitions (id,valid_from,record_version,provenance,is_generated,metric_id,canonical_name,formula,unit,grain) VALUES (?,0,'v1',?,true,?,?,?,?,?)",
            [
                metric.metric_id,
                metric.provenance,
                metric.metric_id,
                metric.canonical_name,
                metric.formula,
                metric.unit,
                metric.grain,
            ],
        )
    counts = {}
    for name in CUSTOM:
        count_row = conn.execute(f"SELECT count(*) FROM {name}").fetchone()
        assert count_row is not None
        counts[name] = count_row[0]
    total_columns = sum(len(BASE) + len(custom) for custom in CUSTOM.values())
    conn.execute("CHECKPOINT")
    conn.close()
    os.chmod(path, 0o444)
    ddl_rel = "warehouse/schema.sql"
    (ROOT / "warehouse").mkdir(exist_ok=True)
    (ROOT / ddl_rel).write_text("\n".join(ddl_lines) + "\n", encoding="utf-8")
    manifest = {
        "generated_at_utc": utc_now(),
        "database_sha256": file_sha256(path),
        "database_bytes": path.stat().st_size,
        "database_path": str(path),
        "table_count": len(CUSTOM),
        "column_count": total_columns,
        "row_counts": counts,
        "T1_parquet_sha256": eda["parquet_sha256"],
        "account_mapping": "hash(campaign) % 20; accounts/tenants are generated and not Criteo labels",
        "fact_provenance": "campaign_daily aggregates all T1 events; impression_events contains first 100000 T1 events",
        "note": "Other table seed rows are controlled synthetic values; no production policy truth is represented",
    }
    rel = "evidence/warehouse/manifest.json"
    atomic_json(ROOT / rel, manifest)
    state = load_state()
    state["dataset_identities"]["T3"] = manifest["database_sha256"]
    save_state(state)
    record(
        "E04",
        "E04-warehouse-v2",
        {"account_count": 20, "impression_sample": 100000},
        {"T1_parquet": eda["parquet_sha256"], "T3": manifest["database_sha256"]},
        {"device_backend": "CPU", "duckdb": duckdb.__version__, "database_readonly": True},
        "PASS",
        [rel, ddl_rel],
        "D",
        started,
    )
    return manifest
