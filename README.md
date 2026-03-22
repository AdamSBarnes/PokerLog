# PokerLog refactor

This repo now hosts a React frontend and FastAPI backend that read from SQLite.

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
- `POKER_SQLITE_PATH`
- `POKER_SEED_CSV`

## Quick start (frontend)

```bash
cd frontend
npm install
npm run dev
```

To point the frontend at another API URL, set `VITE_API_BASE` before running Vite.

## API overview

- `GET /api/metadata`
- `GET /api/games?seasons=1,2`
- `GET /api/player-summary?seasons=1,2`
- `GET /api/losing-streaks?seasons=1,2&n=20&active=false`
- `GET /api/roi-series?seasons=1,2`
- `POST /api/games`
- `PUT /api/games/{game_overall}`
- `DELETE /api/games/{game_overall}`

## Load raw CSV

```bash
python -m backend.load_csv ~/game_20260122.csv
```

Use `--append` to add rows without truncating the table.
