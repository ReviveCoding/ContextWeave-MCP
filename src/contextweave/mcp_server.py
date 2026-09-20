"""Read-only MCP v2 adapter. Protected tools verify signed scope before access."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mcp.server import MCPServer

from contextweave.catalog import METRICS, metric_graph
from contextweave.context import lexical_score
from contextweave.security import SecurityError, run_readonly_sql, validate_sql, verify_token

mcp = MCPServer("ContextWeave-MCP")


def _claims(token: str) -> Any:
    secret = os.environ.get("CONTEXTWEAVE_JWT_SECRET")
    if not secret:
        raise SecurityError("JWT signing secret is not configured")
    claims = verify_token(token, secret, "contextweave-mcp")
    import duckdb

    conn = duckdb.connect(
        str(_database()), read_only=True, config={"enable_external_access": "false"}
    )
    try:
        rows = conn.execute(
            "SELECT account_id,scope,revoked FROM permission_scope "
            "WHERE subject_id = ? AND tenant_id = ?",
            [claims.sub, claims.tenant_id],
        ).fetchall()
    finally:
        conn.close()
    allowed = {row[0] for row in rows if row[1] in claims.scopes and not row[2]}
    if not set(claims.account_ids) <= allowed:
        raise SecurityError("account authorization denied")
    return claims


def _database() -> Path:
    return Path(
        os.environ.get(
            "CONTEXTWEAVE_DB",
            "/home/bjw-0/.cache/contextweave-mcp/warehouse/contextweave_v2.duckdb",
        )
    )


@mcp.resource("schema://catalog")
def schema_catalog() -> str:
    """Public schema object names; data and account scope require authorized tools."""
    return json.dumps(
        {
            "tables": [
                "accounts",
                "campaigns",
                "campaign_daily",
                "impression_events",
                "metric_definitions",
            ]
        }
    )


@mcp.resource("metric://catalog")
def metric_catalog() -> str:
    """Public metric IDs and names; authoritative formulas require authorized tools."""
    return json.dumps(
        [{"metric_id": metric.metric_id, "name": metric.canonical_name} for metric in METRICS]
    )


@mcp.resource("policy://catalog")
def policy_catalog() -> str:
    """Policy discovery URI; scoped policy text is available through retrieve_policy."""
    return json.dumps({"policy_tools": ["retrieve_policy"]})


@mcp.resource("documentation://catalog")
def documentation_catalog() -> str:
    """Public documentation provenance."""
    return json.dumps(
        {
            "openrtb": "https://github.com/InteractiveAdvertisingBureau/openrtb2.x/releases/tag/2.6-202606",
            "synthetic_docs": "generated, not production policy",
        }
    )


@mcp.tool()
def search_schema(query: str, token: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search authorized governed schema objects."""
    _claims(token)
    graph = metric_graph()
    ranked = sorted(
        graph.nodes.values(), key=lambda node: (-lexical_score(query, node.text), node.id)
    )
    return [
        {"id": node.id, "kind": node.kind, "text": node.text}
        for node in ranked[: max(0, min(limit, 50))]
    ]


@mcp.tool()
def describe_schema(table: str, token: str) -> dict[str, Any]:
    """Describe one governed table without exposing rows."""
    _claims(token)
    allowed = {"accounts", "campaigns", "campaign_daily", "impression_events", "metric_definitions"}
    if table not in allowed:
        raise SecurityError("table unavailable")
    import duckdb

    conn = duckdb.connect(
        str(_database()), read_only=True, config={"enable_external_access": "false"}
    )
    try:
        rows = conn.execute(f"DESCRIBE {table}").fetchall()
        return {"table": table, "columns": [{"name": row[0], "type": row[1]} for row in rows]}
    finally:
        conn.close()


@mcp.tool()
def get_metric_definition(metric_id: str, token: str) -> dict[str, Any]:
    """Return an exact governed metric ID, formula and dependencies."""
    _claims(token)
    for metric in METRICS:
        if metric.metric_id == metric_id:
            return {
                "metric_id": metric.metric_id,
                "formula": metric.formula,
                "unit": metric.unit,
                "required_tables": metric.required_tables,
                "required_columns": metric.required_columns,
                "version": metric.version,
                "provenance": metric.provenance,
            }
    raise SecurityError("metric unavailable")


@mcp.tool(name="run_readonly_sql")
def run_readonly_sql_tool(sql: str, token: str) -> dict[str, Any]:
    """Execute one account-scoped analytical SELECT under resource limits."""
    return run_readonly_sql(_database(), sql, _claims(token))


@mcp.tool()
def get_campaign_timeseries(campaign_id: str, token: str) -> dict[str, Any]:
    """Get an authorized campaign's daily impression and click series."""
    claims = _claims(token)
    if not campaign_id.isdecimal():
        raise SecurityError("invalid campaign ID")
    sql = (
        "SELECT campaign_id, day, impressions, clicks, conversions, transformed_cost "
        f"FROM campaign_daily WHERE campaign_id = '{campaign_id}' ORDER BY day"
    )
    return run_readonly_sql(_database(), sql, claims)


@mcp.tool()
def get_freshness(token: str) -> dict[str, Any]:
    """Return source watermark and frozen schema/metric versions."""
    _claims(token)
    from contextweave.evidence import ROOT

    manifest = json.loads((ROOT / "evidence/warehouse/manifest.json").read_text(encoding="utf-8"))
    return {
        "T1_parquet_sha256": manifest["T1_parquet_sha256"],
        "schema_version": "v1",
        "metric_version": "v1",
        "warehouse_frozen": True,
    }


@mcp.tool()
def retrieve_policy(policy_kind: str, token: str) -> dict[str, Any]:
    """Return only account-scoped synthetic policy rows."""
    claims = _claims(token)
    allowed = {
        "budget": "budget_policies",
        "bid": "bid_policies",
        "targeting": "targeting_policies",
        "account": "account_constraints",
    }
    if policy_kind not in allowed:
        raise SecurityError("unknown policy")
    # Policy tables are intentionally excluded from arbitrary SQL; this tool owns their scope.
    table = allowed[policy_kind]
    import duckdb

    conn = duckdb.connect(
        str(_database()), read_only=True, config={"enable_external_access": "false"}
    )
    try:
        account_list = ",".join("'" + account + "'" for account in claims.account_ids)
        rows = conn.execute(
            f"SELECT id, policy_text, severity FROM {table} WHERE tenant_id = ? "
            f"AND account_id IN ({account_list}) LIMIT 100",
            [claims.tenant_id],
        ).fetchall()
        return {
            "generated": True,
            "policies": [{"id": x[0], "text": x[1], "severity": x[2]} for x in rows],
        }
    finally:
        conn.close()


@mcp.tool()
def explain_query(sql: str, token: str) -> dict[str, Any]:
    """Validate and report referenced tables without executing the query."""
    _claims(token)
    return {"allowed": True, "referenced_tables": validate_sql(sql)}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not os.environ.get("CONTEXTWEAVE_JWT_SECRET"):
        raise SystemExit("CONTEXTWEAVE_JWT_SECRET is required")
    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
