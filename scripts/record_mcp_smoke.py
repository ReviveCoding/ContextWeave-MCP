"""Record a verified MCP transport smoke without advancing an older stage pointer."""

import json

from contextweave.evidence import ROOT, record


def main() -> None:
    smoke = json.loads((ROOT / "evidence/mcp/transport_smoke.json").read_text(encoding="utf-8"))
    if smoke["status"] != "PASS" or smoke["sdk"] != "mcp 2.2.0":
        raise RuntimeError("MCP smoke did not pass with pinned SDK")
    for transport in ("in_memory", "stdio", "streamable_http"):
        result = smoke[transport]
        if (
            result["protocol_version"] != "2026-07-28"
            or result["tool_count"] != 8
            or result["metric_call_error"]
        ):
            raise RuntimeError(f"MCP {transport} smoke failed protocol or metric call")
    receipt = record(
        "E01",
        "E01-MCP-transports-v4",
        {"sdk": "2.2.0", "protocol": "2026-07-28", "async_readiness_seconds": 30},
        {},
        {"device_backend": "CPU", "transports": ["stdio", "streamable_http"]},
        "PASS",
        ["evidence/mcp/transport_smoke.json"],
        "Q",
        smoke["timestamp_utc"],
    )
    print(receipt)


if __name__ == "__main__":
    main()
