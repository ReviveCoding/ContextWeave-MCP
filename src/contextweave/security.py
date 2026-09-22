"""Signed local auth harness and conservative analytical SQL validator."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from threading import Timer
from typing import Any

import jwt
from sqlglot import exp, parse, parse_one


class SecurityError(ValueError):
    pass


@dataclass(frozen=True)
class Claims:
    sub: str
    tenant_id: str
    account_ids: tuple[str, ...]
    scopes: frozenset[str]
    aud: str
    iat: int
    exp: int


def verify_token(
    token: str,
    secret: str,
    audience: str,
    revoked_subjects: frozenset[str] = frozenset(),
    required_scope: str = "analytics:read",
) -> Claims:
    try:
        data: dict[str, Any] = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=audience,
            options={"require": ["sub", "tenant_id", "account_ids", "scopes", "aud", "iat", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise SecurityError("invalid authorization token") from exc
    if data["sub"] in revoked_subjects or required_scope not in data["scopes"]:
        raise SecurityError("authorization denied")
    if not isinstance(data["account_ids"], list) or not data["account_ids"]:
        raise SecurityError("account scope required")
    if not isinstance(data["tenant_id"], str) or not re.fullmatch(
        r"[A-Za-z0-9_-]+", data["tenant_id"]
    ):
        raise SecurityError("invalid tenant")
    accounts = tuple(data["account_ids"])
    if any(not isinstance(a, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", a) for a in accounts):
        raise SecurityError("invalid account scope")
    return Claims(
        str(data["sub"]),
        data["tenant_id"],
        accounts,
        frozenset(data["scopes"]),
        audience,
        int(data["iat"]),
        int(data["exp"]),
    )


ALLOWED_FUNCTIONS = frozenset(
    {
        "sum",
        "avg",
        "count",
        "min",
        "max",
        "coalesce",
        "nullif",
        "round",
        "abs",
        "lower",
        "upper",
        "date_trunc",
        "cast",
        "try_cast",
        "floor",
        "ceil",
        "ceiling",
    }
)
ALLOWED_TABLES = frozenset(
    {
        "accounts",
        "advertisers",
        "campaigns",
        "ad_groups",
        "ads",
        "keywords",
        "audiences",
        "products",
        "marketplaces",
        "campaign_config",
        "budget_config",
        "bid_config",
        "targeting_config",
        "conversion_config",
        "impression_events",
        "click_events",
        "conversion_events",
        "campaign_daily",
        "adgroup_daily",
        "keyword_daily",
        "account_daily",
        "auction_daily",
        "metric_definitions",
        "metric_dependencies",
        "business_terms",
        "schema_aliases",
        "budget_policies",
        "bid_policies",
        "targeting_policies",
        "account_constraints",
        "schema_versions",
        "metric_versions",
        "data_freshness",
        "permission_scope",
        "audit_events",
        "cache_versions",
    }
)


def validate_sql(sql: str, allowed_tables: frozenset[str] = ALLOWED_TABLES) -> tuple[str, ...]:
    try:
        statements = parse(sql, read="duckdb")
    except Exception as exc:
        raise SecurityError("invalid SQL syntax") from exc
    if len(statements) != 1 or statements[0] is None:
        raise SecurityError("exactly one SQL statement is required")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        raise SecurityError("only analytical SELECT statements are allowed")
    if any(
        node.key
        in {
            "command",
            "insert",
            "update",
            "delete",
            "create",
            "copy",
            "pragma",
            "attach",
            "drop",
            "export",
            "load",
            "install",
        }
        for node in tree.walk()
    ):
        raise SecurityError("unsafe SQL operation")
    tables: set[str] = set()
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if table.db or table.catalog or name not in allowed_tables:
            raise SecurityError(f"table denied: {name}")
        tables.add(name)
    for function in tree.find_all(exp.Func):
        name = (
            function.name.lower()
            if isinstance(function, exp.Anonymous)
            else function.sql_name().lower()
        )
        if isinstance(function, exp.Anonymous) and name not in ALLOWED_FUNCTIONS:
            raise SecurityError(f"function denied: {name}")
    if not tables:
        raise SecurityError("query must reference an allowed table")
    return tuple(sorted(tables))


def scoped_sql(sql: str, claims: Claims, allowed_tables: frozenset[str] = ALLOWED_TABLES) -> str:
    validate_sql(sql, allowed_tables)
    tree = parse(sql, read="duckdb")[0]
    assert tree is not None
    account_list = ",".join(f"'{account}'" for account in claims.account_ids)
    for table in list(tree.find_all(exp.Table)):
        name = table.name.lower()
        alias = table.alias_or_name
        if name == "metric_definitions":
            continue
        replacement = parse_one(
            f"(SELECT * FROM {name} WHERE tenant_id = '{claims.tenant_id}' "
            f"AND account_id IN ({account_list})) AS {alias}",
            read="duckdb",
        )
        table.replace(replacement)
    return tree.sql(dialect="duckdb")


def run_readonly_sql(
    database: Path,
    sql: str,
    claims: Claims,
    row_limit: int = 1000,
    output_byte_limit: int = 1_000_000,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    import json

    import duckdb

    if row_limit < 1 or output_byte_limit < 1 or timeout_seconds <= 0:
        raise ValueError("invalid query limits")
    scoped = scoped_sql(sql, claims)
    conn = duckdb.connect(str(database), read_only=True, config={"enable_external_access": "false"})
    conn.execute("SET memory_limit='1GB'")
    timer = Timer(timeout_seconds, conn.interrupt)
    timer.start()
    try:
        cursor = conn.execute(f"SELECT * FROM ({scoped}) AS result LIMIT {row_limit + 1}")
        names = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        if len(rows) > row_limit:
            raise SecurityError("row limit exceeded")
        result = {"columns": names, "rows": rows}
        encoded = json.dumps(result, default=str).encode()
        if len(encoded) > output_byte_limit:
            raise SecurityError("output byte limit exceeded")
        return result
    except duckdb.Error as exc:
        raise SecurityError("query failed or timed out") from exc
    finally:
        timer.cancel()
        conn.close()
