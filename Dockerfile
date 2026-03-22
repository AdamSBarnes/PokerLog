# ── Build stage ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ backend/
COPY suitedpockets/ suitedpockets/
COPY sql/ sql/
COPY data/sample_games.csv data/sample_games.csv
COPY start.sh /app/start.sh

# Ensure data directory exists (Fly persistent volume mounts here)
RUN mkdir -p /data

ENV POKER_SQLITE_PATH=/data/poker.sqlite
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["/app/start.sh"]


