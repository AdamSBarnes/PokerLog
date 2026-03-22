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
