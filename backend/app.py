from datetime import date
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from backend.analytics import game_history, losing_streaks, metadata, player_summary, roi_series
from suitedpockets.data import delete_game, insert_game, update_game

app = FastAPI(title="PokerLog API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class GameCreate(BaseModel):
    season: int
    game_date: date
    game_number: int
    stake: int
    winner: str
    is_placings: int

    model_config = ConfigDict(extra="allow")


class GameUpdate(BaseModel):
    season: int | None = None
    game_date: date | None = None
    game_number: int | None = None
    stake: int | None = None
    winner: str | None = None
    is_placings: int | None = None

    model_config = ConfigDict(extra="allow")


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


@app.post("/api/games", status_code=201)
def create_game(payload: GameCreate) -> dict:
    game_id = insert_game(payload.model_dump())
    return {"game_overall": game_id}


@app.put("/api/games/{game_overall}", status_code=204)
def put_game(game_overall: int, payload: GameUpdate) -> None:
    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    update_game(game_overall, updates)


@app.delete("/api/games/{game_overall}", status_code=204)
def remove_game(game_overall: int) -> None:
    delete_game(game_overall)

