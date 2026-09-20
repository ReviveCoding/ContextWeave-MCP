"""MCP v2 in-memory, stdio, and Streamable HTTP transport smoke tests."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from typing import Any

import jwt
from mcp import Client, StdioServerParameters

from contextweave.evidence import ROOT, atomic_json, utc_now
from contextweave.mcp_server import mcp


def _token(secret: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": "analyst_0",
            "tenant_id": "tenant_00",
            "account_ids": ["account_00"],
            "scopes": ["analytics:read"],
            "aud": "contextweave-mcp",
            "iat": now,
            "exp": now + 300,
        },
        secret,
        algorithm="HS256",
    )


async def _exercise(client: Client, token: str) -> dict[str, Any]:
    tools = await client.list_tools()
    names = {tool.name for tool in tools.tools}
    required = {
        "search_schema",
        "describe_schema",
        "get_metric_definition",
        "run_readonly_sql",
        "get_campaign_timeseries",
        "get_freshness",
        "retrieve_policy",
        "explain_query",
    }
    if not required <= names:
        raise AssertionError(f"missing tools: {required - names}")
    result = await client.call_tool("get_metric_definition", {"metric_id": "M_CTR", "token": token})
    if result.is_error:
        raise AssertionError("metric tool failed")
    return {
        "protocol_version": str(client.protocol_version),
        "tool_count": len(names),
        "metric_call_error": bool(result.is_error),
    }


async def run_smoke() -> dict[str, Any]:
    secret = secrets.token_urlsafe(48)
    token = _token(secret)
    db = json.loads((ROOT / "evidence/warehouse/manifest.json").read_text(encoding="utf-8"))[
        "database_path"
    ]
    os.environ["CONTEXTWEAVE_JWT_SECRET"] = secret
    os.environ["CONTEXTWEAVE_DB"] = db
    outcomes: dict[str, Any] = {"timestamp_utc": utc_now(), "sdk": "mcp 2.2.0"}
    async with Client(mcp) as client:
        outcomes["in_memory"] = await _exercise(client, token)
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "contextweave.mcp_server"],
        env={"CONTEXTWEAVE_JWT_SECRET": secret, "CONTEXTWEAVE_DB": db},
    )
    async with Client(server) as client:
        outcomes["stdio"] = await _exercise(client, token)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    env = {**os.environ, "CONTEXTWEAVE_JWT_SECRET": secret, "CONTEXTWEAVE_DB": db}
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "contextweave.mcp_server",
        "--transport",
        "streamable-http",
        "--port",
        str(port),
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        for _ in range(300):
            if process.returncode is not None:
                raise RuntimeError("HTTP server exited before readiness")
            try:
                _reader, writer = await asyncio.open_connection("127.0.0.1", port)
                writer.close()
                await writer.wait_closed()
                break
            except OSError:
                await asyncio.sleep(0.1)
        else:
            raise RuntimeError("HTTP server readiness timeout")
        async with Client(f"http://127.0.0.1:{port}/mcp") as client:
            outcomes["streamable_http"] = await _exercise(client, token)
    finally:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except TimeoutError:
            process.kill()
            await process.wait()
    outcomes["status"] = "PASS"
    atomic_json(ROOT / "evidence/mcp/transport_smoke.json", outcomes)
    return outcomes


def main() -> None:
    print(json.dumps(asyncio.run(run_smoke()), indent=2))


if __name__ == "__main__":
    main()
