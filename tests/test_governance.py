from __future__ import annotations

import time

import jwt
import pytest

from contextweave.benchmark import normalized_hash
from contextweave.cache import CacheIdentity, GovernedCache
from contextweave.catalog import METRICS, metric_graph
from contextweave.context import select_context
from contextweave.security import SecurityError, scoped_sql, validate_sql, verify_token


def test_metric_critical_closure_and_budget() -> None:
    graph = metric_graph()
    metric = next(metric for metric in METRICS if metric.metric_id == "M_CTR")
    closure = graph.closure({metric.metric_id})
    assert "COLUMN:campaign_daily.clicks" in closure
    assert "COLUMN:campaign_daily.impressions" in closure
    eligible = set(graph.nodes)
    result = select_context("CTR", graph, 200, "tenant_00", eligible, eligible, {"M_CTR"})
    assert result.behavior == "ANSWER"
    assert closure <= set(result.selected_ids)
    too_small = select_context("CTR", graph, 1, "tenant_00", eligible, eligible, {"M_CTR"})
    assert too_small.behavior == "ABSTAIN"
    assert not too_small.selected_ids


def test_jwt_and_scoped_sql() -> None:
    now = int(time.time())
    payload = {
        "sub": "analyst",
        "tenant_id": "tenant_00",
        "account_ids": ["account_00"],
        "scopes": ["analytics:read"],
        "aud": "contextweave-test",
        "iat": now,
        "exp": now + 60,
    }
    token = jwt.encode(payload, "test-only-secret", algorithm="HS256")
    claims = verify_token(token, "test-only-secret", "contextweave-test")
    assert claims.tenant_id == "tenant_00"
    scoped = scoped_sql("SELECT sum(clicks) FROM campaign_daily", claims)
    assert "tenant_00" in scoped and "account_00" in scoped
    with pytest.raises(SecurityError):
        verify_token(token, "test-only-secret", "wrong-audience")
    with pytest.raises(SecurityError):
        verify_token(token, "test-only-secret", "contextweave-test", frozenset({"analyst"}))
    with pytest.raises(SecurityError):
        verify_token(
            jwt.encode({**payload, "exp": now - 10}, "test-only-secret", algorithm="HS256"),
            "test-only-secret",
            "contextweave-test",
        )


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM campaigns",
        "CREATE TABLE stolen AS SELECT * FROM campaigns",
        "COPY campaigns TO '/tmp/leak.csv'",
        "SELECT * FROM read_csv('/etc/passwd')",
        "SELECT * FROM main.campaigns",
        "SELECT * FROM campaigns; SELECT * FROM accounts",
        "SELECT read_text('/etc/passwd') FROM campaigns",
        "INSTALL httpfs",
    ],
)
def test_sql_attacks_denied(sql: str) -> None:
    with pytest.raises(SecurityError):
        validate_sql(sql)


def test_cache_isolation_and_freshness() -> None:
    base = CacheIdentity(
        "tenant_00", ("account_00",), ("analytics:read",), "s1", "v1", "m1", 10, "account", "tenant"
    )
    cache = GovernedCache("KC")
    cache.put("question", base, {"answer": 42}, 10)
    assert cache.get("question", base) == {"answer": 42}
    assert (
        cache.get(
            "question",
            CacheIdentity(
                "tenant_01",
                base.account_ids,
                base.scopes,
                base.source_version,
                base.schema_version,
                base.metric_version,
                base.data_watermark,
                base.sensitivity,
                base.cache_scope,
            ),
        )
        is None
    )
    assert (
        cache.get(
            "question",
            CacheIdentity(
                base.tenant_id,
                base.account_ids,
                base.scopes,
                base.source_version,
                base.schema_version,
                base.metric_version,
                11,
                base.sensitivity,
                base.cache_scope,
            ),
        )
        is None
    )
    assert (
        cache.get(
            "question",
            CacheIdentity(
                base.tenant_id,
                base.account_ids,
                (),
                base.source_version,
                base.schema_version,
                base.metric_version,
                base.data_watermark,
                base.sensitivity,
                base.cache_scope,
            ),
        )
        is None
    )


def test_result_equivalence_ignores_alias_and_order() -> None:
    assert normalized_hash(["spend"], [(2.0,), (1.0,)]) == normalized_hash(
        ["total_cost"], [(1.0,), (2.0,)]
    )
    assert normalized_hash(["x"], [(1.0,)]) != normalized_hash(["x", "y"], [(1.0, 2.0)])
