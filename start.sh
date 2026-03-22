#!/bin/bash
set -e

mkdir -p "$(dirname "${POKER_SQLITE_PATH:-/data/poker.sqlite}")"

exec uvicorn backend.app:app --host 0.0.0.0 --port 8000
