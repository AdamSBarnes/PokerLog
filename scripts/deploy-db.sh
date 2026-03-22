#!/bin/bash
# One-time script: deploys the local poker.sqlite to the Fly.io volume.
# Run from the project root. Reverts all temporary changes after deploy.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Temporarily patching build to include local database …"

# 1. Remove poker.sqlite from .dockerignore so Docker can see it
sed -i '/^data\/poker\.sqlite$/d' .dockerignore

# 2. Add COPY to Dockerfile (before the start.sh COPY)
sed -i '/^COPY start\.sh/i COPY data/poker.sqlite data/poker.sqlite.seed' Dockerfile

# 3. Patch start.sh to always copy the seed DB to the volume
sed -i '/^exec uvicorn/i \
# One-time seed: always overwrite with bundled DB\
if [ -f /app/data/poker.sqlite.seed ]; then\
  echo "==> Copying bundled database to volume …"\
  cp -f /app/data/poker.sqlite.seed "$DB_PATH"\
  echo "✓ Done"\
fi\
' start.sh

echo "==> Deploying to Fly.io (local build context) …"
fly deploy

echo "==> Reverting temporary changes …"
git checkout -- .dockerignore Dockerfile start.sh

echo ""
echo "✓ Database deployed. Temporary changes reverted."
echo "  Future deploys via GitHub Actions will work normally."
echo "  IMPORTANT: Now redeploy without the seed to avoid overwriting on every restart:"
echo "    fly deploy  (or push to master to trigger CI)"
