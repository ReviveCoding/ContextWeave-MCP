"""Criteo source validation and bounded DuckDB EDA in native WSL scratch."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from contextweave.evidence import ROOT, atomic_json, load_state, record, save_state, utc_now

SCRATCH = Path("/home/bjw-0/.cache/contextweave-mcp")
CRITEO = SCRATCH / "source/criteo_attribution_dataset.tsv.gz"
SPIDER = SCRATCH / "source/Spider2/spider2-dbt"
EXPECTED_COLUMNS = [
    "timestamp",
    "uid",
    "campaign",
    "conversion",
    "conversion_timestamp",
    "conversion_id",
    "attribution",
    "click",
    "click_pos",
    "click_nb",
    "cost",
    "cpo",
    "time_since_last_click",
    "cat1",
    "cat2",
    "cat3",
    "cat4",
    "cat5",
    "cat6",
    "cat7",
    "cat8",
    "cat9",
]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source_validation() -> dict[str, Any]:
    started = utc_now()
    if not CRITEO.is_file() or not SPIDER.is_dir():
        raise FileNotFoundError("Criteo archive and Spider2-DBT checkout are both required")
    with gzip.open(CRITEO, "rt", encoding="utf-8", newline="") as f:
        header = f.readline().rstrip("\r\n").split("\t")
        if header != EXPECTED_COLUMNS:
            raise ValueError(f"unexpected Criteo schema: {header}")
        count = sum(block.count("\n") for block in iter(lambda: f.read(8 * 1024 * 1024), ""))
    if count < 16_000_000:
        raise ValueError(f"truncated Criteo source: {count} events")
    task_manifest = SPIDER / "examples/spider2-dbt.jsonl"
    evaluator = SPIDER / "evaluation_suite/evaluate.py"
    task_count = sum(1 for line in task_manifest.open(encoding="utf-8") if line.strip())
    import subprocess

    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SPIDER, text=True).strip()
    source: dict[str, Any] = {
        "timestamp_utc": utc_now(),
        "criteo": {
            "source": "Criteo-owned Hugging Face mirror",
            "mirror_revision": "904188a63cbad78bee43cd26ff5ee4ac77903986",
            "archive_sha256": file_sha256(CRITEO),
            "compressed_bytes": CRITEO.stat().st_size,
            "validated_event_count": count,
            "columns": header,
            "license": "CC BY-NC-SA 4.0",
            "raw_location": str(CRITEO),
        },
        "spider2_dbt": {
            "commit": commit,
            "task_count": task_count,
            "manifest_sha256": file_sha256(task_manifest),
            "evaluator_sha256": file_sha256(evaluator),
            "scratch_location": str(SPIDER),
        },
    }
    if task_count != 68:
        raise ValueError(f"unexpected Spider2-DBT task count: {task_count}")
    rel = "evidence/sources/validated.json"
    atomic_json(ROOT / rel, source)
    registry_path = ROOT / "sources/registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    criteo = registry["sources"][0]
    criteo.update(
        {
            "version_or_commit": source["criteo"]["mirror_revision"],
            "retrieved_at": source["timestamp_utc"],
            "compressed_bytes": source["criteo"]["compressed_bytes"],
            "sha256": source["criteo"]["archive_sha256"],
            "status": "validated",
        }
    )
    spider = registry["sources"][1]
    spider.update(
        {
            "version_or_commit": commit,
            "retrieved_at": source["timestamp_utc"],
            "sha256": source["spider2_dbt"]["manifest_sha256"],
            "status": "manifest validated; evaluator not yet executed",
        }
    )
    atomic_json(registry_path, registry)
    state = load_state()
    state["dataset_identities"] = {
        "T1": source["criteo"]["archive_sha256"],
        "T4_manifest": source["spider2_dbt"]["manifest_sha256"],
    }
    save_state(state)
    record(
        "E02",
        "E02-source-validation",
        {"min_criteo_rows": 16_000_000, "spider_tasks": 68},
        state["dataset_identities"],
        {"device_backend": "CPU", "scratch": str(SCRATCH)},
        "PASS",
        [rel, "sources/registry.json"],
        "D",
        started,
    )
    return source


def eda() -> dict[str, Any]:
    import duckdb

    started = utc_now()
    if not (ROOT / "evidence/sources/validated.json").exists():
        raise RuntimeError("E02 validation must pass before E03")
    scratch = SCRATCH / "curated"
    scratch.mkdir(parents=True, exist_ok=True)
    parquet = scratch / "criteo_events.parquet"
    db = duckdb.connect()
    db.execute("SET memory_limit='8GB'")
    db.execute(f"SET temp_directory='{SCRATCH / 'duckdb_tmp'}'")
    source_path = str(CRITEO).replace("'", "''")
    parquet_path = str(parquet).replace("'", "''")
    if not parquet.is_file():
        db.execute(
            "COPY (SELECT "
            "TRY_CAST(timestamp AS BIGINT) AS timestamp, uid, campaign, "
            "TRY_CAST(conversion AS INTEGER) AS conversion, "
            "TRY_CAST(conversion_timestamp AS BIGINT) AS conversion_timestamp, "
            "conversion_id, TRY_CAST(attribution AS INTEGER) AS attribution, "
            "TRY_CAST(click AS INTEGER) AS click, "
            "TRY_CAST(click_pos AS INTEGER) AS click_pos, "
            "TRY_CAST(click_nb AS INTEGER) AS click_nb, "
            "TRY_CAST(cost AS DOUBLE) AS cost, TRY_CAST(cpo AS DOUBLE) AS cpo, "
            "TRY_CAST(time_since_last_click AS BIGINT) AS time_since_last_click, "
            + ", ".join(f"cat{i}" for i in range(1, 10))
            + f" FROM read_csv('{source_path}', delim='\t', header=true, all_varchar=true, null_padding=false)) "
            + f"TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
    db.execute(f"CREATE VIEW events AS SELECT * FROM read_parquet('{parquet_path}')")
    totals = db.execute(
        "SELECT count(*) n, min(timestamp) min_ts, max(timestamp) max_ts, "
        "count(DISTINCT uid) users, count(DISTINCT campaign) campaigns, "
        "sum(click) clicks, sum(conversion) conversion_rows, sum(attribution) attributed_rows, "
        "min(cost) min_cost, max(cost) max_cost, sum(cost) total_transformed_cost, "
        "count(*) FILTER (WHERE timestamp IS NULL OR conversion IS NULL OR click IS NULL "
        "OR cost IS NULL OR uid IS NULL OR campaign IS NULL) malformed_rows, "
        "count(*) FILTER (WHERE click NOT IN (0,1) OR conversion NOT IN (0,1) "
        "OR attribution NOT IN (0,1) OR cost < 0) domain_invalid_rows "
        "FROM events"
    )
    cols = [x[0] for x in totals.description]
    values = totals.fetchone()
    assert values is not None
    summary = dict(zip(cols, values, strict=True))
    nulls = db.execute(
        "SELECT "
        + ",".join(f"count(*) FILTER (WHERE {name} IS NULL) AS {name}" for name in EXPECTED_COLUMNS)
        + " FROM events"
    ).fetchone()
    summary["null_counts"] = dict(zip(EXPECTED_COLUMNS, nulls, strict=True)) if nulls else {}
    summary["daily"] = [
        dict(zip(("day", "events", "clicks", "conversions", "cost"), row, strict=True))
        for row in db.execute(
            "SELECT floor(timestamp / 86400)::INTEGER AS day_index, count(*), sum(click), "
            "sum(conversion), sum(cost) FROM events GROUP BY 1 ORDER BY 1"
        ).fetchall()
    ]
    summary["top_campaigns"] = [
        dict(zip(("campaign", "events", "clicks", "conversions"), row, strict=True))
        for row in db.execute(
            "SELECT campaign, count(*), sum(click), sum(conversion) FROM events "
            "GROUP BY campaign ORDER BY count(*) DESC LIMIT 10"
        ).fetchall()
    ]
    max_user_row = db.execute(
        "SELECT max(n) FROM (SELECT count(*) n FROM events GROUP BY uid)"
    ).fetchone()
    assert max_user_row is not None
    summary["max_user_events"] = max_user_row[0]
    hash_args = ",".join(EXPECTED_COLUMNS)
    duplicate_row = db.execute(
        f"SELECT count(*) - count(DISTINCT hash({hash_args})) FROM events"
    ).fetchone()
    assert duplicate_row is not None
    summary["duplicate_hash_rows"] = duplicate_row[0]
    summary["duplicate_note"] = "64-bit row-hash proxy; hash collisions are possible"
    summary["parquet_bytes"] = parquet.stat().st_size
    summary["parquet_sha256"] = file_sha256(parquet)
    rel = "evidence/data/criteo_eda.json"
    atomic_json(ROOT / rel, summary)
    lines = [
        "# T1 Criteo data audit",
        "",
        "Canonical aggregate: `evidence/data/criteo_eda.json`. T1 is real public event structure, not incident or policy truth.",
        "",
    ]
    for key in (
        "n",
        "min_ts",
        "max_ts",
        "users",
        "campaigns",
        "clicks",
        "conversion_rows",
        "attributed_rows",
        "malformed_rows",
        "domain_invalid_rows",
        "duplicate_hash_rows",
        "max_user_events",
    ):
        lines.append(f"- {key}: {summary[key]}")
    lines += [
        "",
        "Costs are transformed values, not real paid amounts. Conversion labels and attribution are future-looking; task construction must avoid temporal leakage.",
        "Daily distributions, null counts, and campaign concentration are in the canonical JSON. The duplicate count is a hash-based proxy.",
    ]
    (ROOT / "reports/DATA_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    record(
        "E03",
        "E03-criteo-eda",
        {"parquet_compression": "zstd", "source": file_sha256(CRITEO)},
        {"T1": file_sha256(CRITEO), "parquet": summary["parquet_sha256"]},
        {"device_backend": "CPU", "duckdb": duckdb.__version__, "scratch": str(SCRATCH)},
        "PASS",
        [rel, "reports/DATA_AUDIT.md"],
        "D",
        started,
    )
    return summary
