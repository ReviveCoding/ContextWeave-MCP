"""Governed metric definitions; downstream context uses immutable IDs and formulas."""

from __future__ import annotations

from dataclasses import dataclass

from contextweave.graph import DependencyGraph, Edge, Node


@dataclass(frozen=True)
class Metric:
    metric_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    formula: str
    required_tables: tuple[str, ...]
    required_columns: tuple[str, ...]
    grain: str
    unit: str
    freshness: str
    sensitivity: str
    authorization_scope: str
    version: str
    provenance: str


METRICS = (
    Metric(
        "M_CTR",
        "CTR",
        ("click-through rate",),
        "SUM(clicks)/NULLIF(SUM(impressions),0)",
        ("campaign_daily",),
        ("campaign_daily.clicks", "campaign_daily.impressions"),
        "campaign-day",
        "ratio",
        "daily",
        "account",
        "analytics:read",
        "v1",
        "controlled synthetic metric",
    ),
    Metric(
        "M_CVR",
        "CVR",
        ("conversion rate",),
        "SUM(conversions)/NULLIF(SUM(clicks),0)",
        ("campaign_daily",),
        ("campaign_daily.conversions", "campaign_daily.clicks"),
        "campaign-day",
        "ratio",
        "daily",
        "account",
        "analytics:read",
        "v1",
        "controlled synthetic metric",
    ),
    Metric(
        "M_SPEND",
        "spend",
        ("cost",),
        "SUM(transformed_cost)",
        ("campaign_daily",),
        ("campaign_daily.transformed_cost",),
        "campaign-day",
        "transformed cost unit",
        "daily",
        "account",
        "analytics:read",
        "v1",
        "derived from transformed Criteo cost",
    ),
    Metric(
        "M_CPA",
        "CPA",
        ("cost per attributed action",),
        "SUM(transformed_cost)/NULLIF(SUM(attributed_conversions),0)",
        ("campaign_daily",),
        ("campaign_daily.transformed_cost", "campaign_daily.attributed_conversions"),
        "campaign-day",
        "transformed cost unit/action",
        "daily",
        "account",
        "analytics:read",
        "v1",
        "controlled synthetic metric",
    ),
    Metric(
        "M_ATTR_CONV",
        "attributed conversions",
        ("credited orders",),
        "SUM(attributed_conversions)",
        ("campaign_daily",),
        ("campaign_daily.attributed_conversions",),
        "campaign-day",
        "count",
        "daily",
        "account",
        "analytics:read",
        "v1",
        "Criteo attribution field aggregation",
    ),
    Metric(
        "M_ATTR_VALUE",
        "attributed value",
        ("credited value",),
        "SUM(attributed_value)",
        ("campaign_daily",),
        ("campaign_daily.attributed_value",),
        "campaign-day",
        "synthetic value unit",
        "daily",
        "account",
        "analytics:read",
        "v1",
        "generated controlled extension",
    ),
    Metric(
        "M_ROAS",
        "ROAS",
        ("return on ad spend",),
        "SUM(attributed_value)/NULLIF(SUM(transformed_cost),0)",
        ("campaign_daily",),
        ("campaign_daily.attributed_value", "campaign_daily.transformed_cost"),
        "campaign-day",
        "ratio of synthetic value to transformed cost",
        "daily",
        "account",
        "analytics:read",
        "v1",
        "controlled synthetic metric; not production ROAS",
    ),
)


def metric_graph() -> DependencyGraph:
    nodes: list[Node] = []
    edges: list[Edge] = []
    table_names = sorted({table for metric in METRICS for table in metric.required_tables})
    column_names = sorted({column for metric in METRICS for column in metric.required_columns})
    for table in table_names:
        nodes.append(Node(f"TABLE:{table}", "TABLE", table, 8))
    for column in column_names:
        nodes.append(Node(f"COLUMN:{column}", "COLUMN", column, 6))
        edges.append(Edge(f"COLUMN:{column}", f"TABLE:{column.split('.')[0]}", "metric_requires"))
    for metric in METRICS:
        nodes.append(
            Node(
                metric.metric_id,
                "METRIC",
                f"{metric.canonical_name}: {metric.formula} [{metric.unit}]",
                24,
            )
        )
        for table in metric.required_tables:
            edges.append(Edge(metric.metric_id, f"TABLE:{table}", "metric_requires"))
        for column in metric.required_columns:
            edges.append(Edge(metric.metric_id, f"COLUMN:{column}", "metric_requires"))
    return DependencyGraph(nodes, edges)
