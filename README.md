# PokerLog

React + FastAPI poker game tracker with normalized SQLite database, JWT-protected admin, and analytics dashboard.

## Architecture

- **Frontend**: React 18 + Vite + Plotly (dashboards, streaks, game history, admin panel)
- **Backend**: FastAPI + pandas analytics
- **Database**: SQLite with 3 normalized tables (`player`, `game`, `game_result`)
- **Auth**: Simple single-user JWT (password-based, admin-only write endpoints)

## Quick start (backend)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.smoketest
uvicorn backend.app:app --reload
```

Backend defaults:
- SQLite file: `data/poker.sqlite`
- Seed CSV: `data/sample_games.csv`

Environment overrides:
- `POKER_SQLITE_PATH` — path to SQLite database
- `POKER_SEED_CSV` — path to seed CSV
- `POKERLOG_ADMIN_PASSWORD` — admin password (default: `admin`)
- `POKERLOG_JWT_SECRET` — JWT signing secret (default: `change-me-in-production`)

## Quick start (frontend)

```bash
cd frontend
npm install
npm run dev
```

To point the frontend at another API URL, set `VITE_API_BASE` before running Vite.

## API overview

### Public (no auth)
- `GET  /api/health`
- `GET  /api/metadata`
- `GET  /api/games?seasons=1,2`
- `GET  /api/player-summary?seasons=1,2`
- `GET  /api/losing-streaks?seasons=1,2&n=20&active=false`
- `GET  /api/roi-series?seasons=1,2`
- `GET  /api/players`

### Auth
- `POST /api/login` — `{ "password": "..." }` → returns JWT token

### Admin (requires `Authorization: Bearer <token>`)
- `POST   /api/games` — create game with results
- `PUT    /api/games/{id}` — update game
- `DELETE /api/games/{id}` — delete game
- `POST   /api/players` — add player
- `PUT    /api/players/{id}` — update player
- `DELETE /api/players/{id}` — deactivate player

## Database schema

```
player(player_id, name, display_name, active)
game(game_overall, season, game_date, game_number, stake, winner, is_placings)
game_result(id, game_overall→game, player_id→player, finish_position)
```

Auto-migration from the old wide-format schema runs on first access.

## Load raw CSV

```bash
python -m backend.load_csv ~/game_data.csv
```

Use `--append` to add rows without truncating the table.

---

## Deployment

The production stack runs on **free tiers**:

| Component | Service | Cost |
|-----------|---------|------|
| Backend   | Fly.io (shared-cpu-1x, 256 MB) | $0/mo |
| Database  | SQLite on Fly.io persistent volume | $0/mo |
| Frontend  | Netlify | $0/mo |
| CI/CD     | GitHub Actions | $0/mo |

### 1. Backend — Fly.io

#### First-time setup

```bash
# Install the Fly CLI
curl -L https://fly.io/install.sh | sh

# Authenticate
fly auth login

# Create the app (run once from the project root)
fly apps create suitedpockets

# Create a 1 GB persistent volume for the SQLite database
fly volumes create suitedpockets_data --region syd --size 1

# Set secrets (these are encrypted, never stored in config)
fly secrets set \
  POKERLOG_ADMIN_PASSWORD="your-strong-password" \
  POKERLOG_JWT_SECRET="$(openssl rand -hex 32)"

# Deploy
fly deploy
```

You can also generate secrets from CI — go to **Actions → Setup / Rotate Secrets → Run workflow** in your GitHub repo. This auto-generates the JWT secret and optionally the admin password, then pushes them to Fly.

To rotate just the JWT secret later:

```bash
./scripts/setup-secrets.sh --rotate-jwt
```

#### How it works

- `Dockerfile` builds a slim Python image and runs uvicorn.
- The `/data` directory is a Fly persistent volume so the SQLite database
  survives restarts and re-deploys.
- `fly.toml` configures auto-stop/auto-start so the machine sleeps when idle
  (no cost while sleeping).

#### Manual deploy

```bash
fly deploy
```

### 2. Database backup

Keep a local copy of the SQLite database. You can pull it from Fly at any time:

```bash
fly ssh sftp get /data/poker.sqlite ./data/poker.sqlite
```

### 3. Frontend — Netlify

1. Connect the GitHub repo to Netlify (or use the CLI).
2. Set the **build settings** (also in `netlify.toml`):
   - Base directory: `frontend/`
   - Build command: `npm ci && npm run build`
   - Publish directory: `frontend/dist`
3. Add the environment variable in the Netlify dashboard:
   - `VITE_API_BASE` = `https://suitedpockets.fly.dev` (your Fly app URL)

Pushes to `main` auto-deploy via GitHub Actions or Netlify's built-in CI.

### 4. CI/CD — GitHub Actions

Three workflows:

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `deploy-backend.yml` | Push to `main` (backend paths) | Builds & deploys to Fly.io |
| `deploy-frontend.yml` | Push to `main` (frontend paths) | Builds & deploys to Netlify |
| `setup-secrets.yml` | Manual (Actions → Run workflow) | Generates & pushes secrets to Fly.io |

#### Required GitHub secrets / variables

| Name | Where | Purpose |
|------|-------|---------|
| `FLY_API_TOKEN` | Secret | `fly tokens create deploy -x 999999h` |
| `NETLIFY_AUTH_TOKEN` | Secret | Netlify personal access token |
| `NETLIFY_SITE_ID` | Secret | Netlify site API ID |
| `VITE_API_BASE` | Variable | Backend URL, e.g. `https://suitedpockets.fly.dev` |

### 5. CORS

In production, set the `POKERLOG_CORS_ORIGINS` Fly secret to your Netlify
domain to lock down cross-origin requests:

```bash
fly secrets set POKERLOG_CORS_ORIGINS="https://your-site.netlify.app"
```


