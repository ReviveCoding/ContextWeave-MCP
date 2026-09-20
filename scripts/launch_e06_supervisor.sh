#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/bjw-0/Downloads/ContextWeave-MCP
nohup setsid /home/bjw-0/.cache/contextweave-mcp/venv/bin/python -u scripts/supervise_e06_c1.py \
  > /home/bjw-0/.cache/contextweave-mcp/e06_c1_supervisor_detached.log 2>&1 \
  < /dev/null &
sleep 2
ps -ef | grep '[p]ython -u scripts/supervise_e06_c1.py'
