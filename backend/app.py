import os
from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.analytics import game_history, losing_streaks, metadata, player_summary, predictions, roi_series
from backend.auth import create_access_token, get_current_admin, verify_password
from suitedpockets.data import (
    create_player,
    deactivate_player,
    delete_game,
    insert_game,
    list_players,
    update_game,
    update_player,
)

app = FastAPI(title="PokerLog API", version="0.2.0")

# In production set POKERLOG_CORS_ORIGINS to your frontend URL, e.g.
# "https://your-site.netlify.app"  (comma-separated for multiple origins)
_raw_origins = os.environ.get("POKERLOG_CORS_ORIGINS", "*")
_allowed_origins = [o.strip() for o in _raw_origins.split(",")] if _raw_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    password: str


class ResultEntry(BaseModel):
    player_id: int
    finish_position: int


class GameCreate(BaseModel):
    season: int
    game_date: date
    game_number: int
    stake: int
    winner: str | None = None
    is_placings: int = 1
    results: list[ResultEntry] = []


class GameUpdate(BaseModel):
    season: int | None = None
    game_date: date | None = None
    game_number: int | None = None
    stake: int | None = None
    winner: str | None = None
    is_placings: int | None = None
    results: list[ResultEntry] | None = None


class PlayerCreate(BaseModel):
    name: str
    display_name: str


class PlayerUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    active: int | None = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/login")
def login(body: LoginRequest) -> dict:
    if not verify_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_access_token()
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Public read endpoints (no auth required)
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/metadata")
def get_metadata() -> dict:
    return metadata()


@app.get("/api/games")
def get_games(seasons: str | None = None) -> list[dict]:
    season_list = [int(s) for s in seasons.split(",")] if seasons else None
    return game_history(season_list)


@app.get("/api/player-summary")
def get_player_summary(seasons: str | None = None) -> list[dict]:
    season_list = [int(s) for s in seasons.split(",")] if seasons else None
    return player_summary(season_list)


@app.get("/api/losing-streaks")
def get_losing_streaks(seasons: str | None = None, n: int = 20, active: bool = False) -> list[dict]:
    season_list = [int(s) for s in seasons.split(",")] if seasons else None
    return losing_streaks(season_list, n=n, active_only=active)


@app.get("/api/roi-series")
def get_roi_series(seasons: str | None = None) -> list[dict]:
    season_list = [int(s) for s in seasons.split(",")] if seasons else None
    return roi_series(season_list)


@app.get("/api/players")
def get_players() -> list[dict]:
    return list_players()


@app.get("/api/predictions")
def get_predictions() -> list[dict]:
    return predictions()


# ---------------------------------------------------------------------------
# Admin endpoints (auth required)
# ---------------------------------------------------------------------------

@app.post("/api/games", status_code=201)
def create_game(payload: GameCreate, _admin: str = Depends(get_current_admin)) -> dict:
    data = payload.model_dump()
    data["game_date"] = str(data["game_date"])
    data["results"] = [r.model_dump() for r in payload.results]
    game_id = insert_game(data)
    return {"game_overall": game_id}


@app.put("/api/games/{game_overall}", status_code=204)
def put_game(game_overall: int, payload: GameUpdate, _admin: str = Depends(get_current_admin)) -> None:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    if "game_date" in updates and updates["game_date"] is not None:
        updates["game_date"] = str(updates["game_date"])
    if "results" in updates and updates["results"] is not None:
        updates["results"] = [r.model_dump() for r in payload.results]
    update_game(game_overall, updates)


@app.delete("/api/games/{game_overall}", status_code=204)
def remove_game(game_overall: int, _admin: str = Depends(get_current_admin)) -> None:
    delete_game(game_overall)


@app.post("/api/players", status_code=201)
def add_player(payload: PlayerCreate, _admin: str = Depends(get_current_admin)) -> dict:
    player_id = create_player(payload.name, payload.display_name)
    return {"player_id": player_id}


@app.put("/api/players/{player_id}", status_code=204)
def edit_player(player_id: int, payload: PlayerUpdate, _admin: str = Depends(get_current_admin)) -> None:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    update_player(player_id, updates)


@app.delete("/api/players/{player_id}", status_code=204)
def remove_player(player_id: int, _admin: str = Depends(get_current_admin)) -> None:
    deactivate_player(player_id)
