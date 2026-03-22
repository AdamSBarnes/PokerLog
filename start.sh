#!/bin/bash
set -e

DB_PATH="${POKER_SQLITE_PATH:-/data/poker.sqlite}"
mkdir -p "$(dirname "$DB_PATH")"


exec uvicorn backend.app:app --host 0.0.0.0 --port 8000

