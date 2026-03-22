#!/bin/bash
set -e

DB_PATH="${POKER_SQLITE_PATH:-/data/poker.sqlite}"
mkdir -p "$(dirname "$DB_PATH")"

# First boot: copy bundled database to the persistent volume
if [ ! -f "$DB_PATH" ] && [ -f /app/data/poker.sqlite.seed ]; then
  echo "==> No database on volume. Copying bundled seed database …"
  cp /app/data/poker.sqlite.seed "$DB_PATH"
  echo "✓ Database copied to $DB_PATH"
fi

exec uvicorn backend.app:app --host 0.0.0.0 --port 8000

