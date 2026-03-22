import os
import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "data" / "poker.sqlite"
DEFAULT_SEED_CSV = ROOT_DIR / "data" / "sample_games.csv"

STANDARD_COLUMNS = [
    "game_overall",
    "season",
    "game_date",
    "game_number",
    "stake",
    "winner",
    "is_placings",
]

PLAYER_COLUMN_MAP = {
    "cedric": "Cedric",
    "daleo": "Dale-O",
    "knottorious": "Knottorious",
    "elcraigo": "El-Craigo",
    "nik": "Nik",
    "nut": "Nut",
}


def _db_path() -> Path:
    return Path(os.environ.get("POKER_SQLITE_PATH", DEFAULT_DB_PATH))


def _seed_csv_path() -> Path:
    return Path(os.environ.get("POKER_SEED_CSV", DEFAULT_SEED_CSV))


def _connect() -> sqlite3.Connection:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS game (
            game_overall INTEGER,
            season INTEGER,
            game_date TEXT,
            game_number INTEGER,
            stake INTEGER,
            winner TEXT,
            is_placings INTEGER
        )
        """
    )


def _table_columns(conn: sqlite3.Connection) -> list[str]:
    info = conn.execute("PRAGMA table_info('game')").fetchall()
    return [row[1] for row in info]


def _ensure_seed_data(conn: sqlite3.Connection) -> None:
    _ensure_schema(conn)
    count = conn.execute("SELECT COUNT(*) FROM game").fetchone()[0]
    if count:
        return
    seed_csv = _seed_csv_path()
    if not seed_csv.exists():
        return
    df = pd.read_csv(seed_csv)
    _insert_dataframe(conn, df)


def _player_columns(conn: sqlite3.Connection) -> list[str]:
    columns = _table_columns(conn)
    return [col for col in columns if col not in STANDARD_COLUMNS]


def _ensure_player_columns(conn: sqlite3.Connection, players: Iterable[str]) -> None:
    existing = set(_table_columns(conn))
    for player in players:
        if player not in existing:
            conn.execute(f"ALTER TABLE game ADD COLUMN {_quote_identifier(player)} INTEGER DEFAULT 0")


def _quote_identifier(name: str) -> str:
    safe = name.replace('"', '""')
    return f'"{safe}"'


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {col: PLAYER_COLUMN_MAP.get(col, col) for col in df.columns}
    return df.rename(columns=rename_map)


def _coerce_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _insert_dataframe(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    df = _normalize_columns(df)
    _ensure_schema(conn)
    player_columns = [col for col in df.columns if col not in STANDARD_COLUMNS]
    _ensure_player_columns(conn, player_columns)
    columns = list(df.columns)
    placeholders = ",".join("?" for _ in columns)
    column_sql = ",".join(_quote_identifier(col) for col in columns)
    rows = [tuple(_coerce_value(row[col]) for col in columns) for row in df.to_dict(orient="records")]
    conn.executemany(
        f"INSERT INTO game ({column_sql}) VALUES ({placeholders})",
        rows,
    )
    conn.commit()


def load_games() -> pd.DataFrame:
    with _connect() as conn:
        _ensure_seed_data(conn)
        df = pd.read_sql_query("SELECT * FROM game ORDER BY game_overall", conn)
    if not df.empty:
        df["game_date"] = pd.to_datetime(df["game_date"]).dt.date
    return df


def list_games(seasons: list[int] | None = None) -> pd.DataFrame:
    with _connect() as conn:
        _ensure_seed_data(conn)
        if seasons:
            placeholders = ",".join("?" for _ in seasons)
            query = f"SELECT * FROM game WHERE season IN ({placeholders}) ORDER BY game_overall"
            df = pd.read_sql_query(query, conn, params=seasons)
        else:
            df = pd.read_sql_query("SELECT * FROM game ORDER BY game_overall", conn)
    if not df.empty:
        df["game_date"] = pd.to_datetime(df["game_date"]).dt.date
    return df


def get_metadata() -> dict:
    with _connect() as conn:
        _ensure_seed_data(conn)
        players = _player_columns(conn)
        seasons = [row[0] for row in conn.execute("SELECT DISTINCT season FROM game ORDER BY season").fetchall()]
    return {"players": players, "seasons": seasons}


def insert_game(payload: dict) -> int:
    with _connect() as conn:
        _ensure_seed_data(conn)
        players = _player_columns(conn)
        _ensure_player_columns(conn, payload.keys())
        players = _player_columns(conn)
        next_id = conn.execute("SELECT COALESCE(MAX(game_overall), 0) + 1 FROM game").fetchone()[0]
        record = {col: payload.get(col) for col in STANDARD_COLUMNS if col != "game_overall"}
        record["game_overall"] = next_id
        for player in players:
            record[player] = int(payload.get(player, 0) or 0)
        columns = list(record.keys())
        placeholders = ",".join("?" for _ in columns)
        column_sql = ",".join(_quote_identifier(col) for col in columns)
        conn.execute(
            f"INSERT INTO game ({column_sql}) VALUES ({placeholders})",
            [_coerce_value(record[col]) for col in columns],
        )
        conn.commit()
    return int(next_id)


def update_game(game_overall: int, payload: dict) -> None:
    if not payload:
        return
    with _connect() as conn:
        _ensure_seed_data(conn)
        _ensure_player_columns(conn, payload.keys())
        columns = [col for col in payload.keys() if col != "game_overall"]
        if not columns:
            return
        assignments = ",".join(f"{_quote_identifier(col)} = ?" for col in columns)
        values = [_coerce_value(payload[col]) for col in columns]
        values.append(game_overall)
        conn.execute(f"UPDATE game SET {assignments} WHERE game_overall = ?", values)
        conn.commit()


def delete_game(game_overall: int) -> None:
    with _connect() as conn:
        _ensure_seed_data(conn)
        conn.execute("DELETE FROM game WHERE game_overall = ?", [game_overall])
        conn.commit()


def load_games_from_csv(csv_path: Path | str, replace: bool = True) -> int:
    path = Path(csv_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(path)
    df = _normalize_columns(df)
    with _connect() as conn:
        _ensure_schema(conn)
        player_columns = [col for col in df.columns if col not in STANDARD_COLUMNS]
        _ensure_player_columns(conn, player_columns)
        if replace:
            conn.execute("DELETE FROM game")
            conn.commit()
        _insert_dataframe(conn, df)
        count = conn.execute("SELECT COUNT(*) FROM game").fetchone()[0]
    return int(count)

