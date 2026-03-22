#!/bin/bash
# Generate and set all required Fly.io secrets in one shot.
# Run once after `fly apps create`, or any time you want to rotate secrets.
#
# Usage:
#   ./scripts/setup-secrets.sh                  # generate + set
#   ./scripts/setup-secrets.sh --rotate-jwt     # rotate only the JWT secret
#
set -euo pipefail

APP="${FLY_APP:-suitedpockets}"

echo "==> Generating secrets for Fly app: $APP"

# Admin password — prompt or generate
if [ "${1:-}" = "--rotate-jwt" ]; then
    JWT_SECRET=$(openssl rand -hex 32)
    echo "==> Rotating JWT secret …"
    fly secrets set POKERLOG_JWT_SECRET="$JWT_SECRET" --app "$APP"
    echo "✓ JWT secret rotated."
    exit 0
fi

# Generate values
JWT_SECRET=$(openssl rand -hex 32)

# Prompt for the admin password (or accept from env)
if [ -n "${POKERLOG_ADMIN_PASSWORD:-}" ]; then
    ADMIN_PW="$POKERLOG_ADMIN_PASSWORD"
else
    read -rsp "Admin password (enter to auto-generate): " ADMIN_PW
    echo
    if [ -z "$ADMIN_PW" ]; then
        ADMIN_PW=$(openssl rand -base64 18)
        echo "  Generated admin password: $ADMIN_PW"
        echo "  (save this somewhere — it won't be shown again)"
    fi
fi

# Push to Fly (encrypted at rest, injected as env vars at runtime)
fly secrets set \
    POKERLOG_ADMIN_PASSWORD="$ADMIN_PW" \
    POKERLOG_JWT_SECRET="$JWT_SECRET" \
    --app "$APP"

echo ""
echo "✓ All secrets set on '$APP'."
echo "  Admin password : ${ADMIN_PW}"
echo "  JWT secret     : (set — not displayed)"


