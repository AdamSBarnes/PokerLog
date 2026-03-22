import os
import sqlite3
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "data" / "poker.sqlite"
DEFAULT_SEED_CSV = ROOT_DIR / "data" / "sample_games.csv"

# Columns in the legacy wide-format CSV / old game table
STANDARD_COLUMNS = [
    "game_overall",
    "season",
    "game_date",
    "game_number",
    "stake",
    "winner",
    "is_placings",
]

# Maps old DB column names → display names for migration
PLAYER_COLUMN_MAP = {
    "cedric": "Cedric",
    "daleo": "Dale-O",
    "knottorious": "Knottorious",
    "elcraigo": "El-Craigo",
    "nik": "Nik",
    "nut": "Nut",
}


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

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
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS player (
            player_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL UNIQUE,
            display_name TEXT    NOT NULL,
            active       INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS game (
            game_overall INTEGER PRIMARY KEY,
            season       INTEGER NOT NULL,
            game_date    TEXT    NOT NULL,
            game_number  INTEGER NOT NULL,
            stake        INTEGER NOT NULL,
            winner       TEXT,
            is_placings  INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS game_result (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            game_overall    INTEGER NOT NULL REFERENCES game(game_overall) ON DELETE CASCADE,
            player_id       INTEGER NOT NULL REFERENCES player(player_id),
            finish_position INTEGER NOT NULL,
            UNIQUE(game_overall, player_id)
        );
        """
    )


def _all_known_player_names() -> set[str]:
    """Return all known player column names (both raw and display forms)."""
    names = set(PLAYER_COLUMN_MAP.keys()) | set(PLAYER_COLUMN_MAP.values())
    return names


def _needs_migration(conn: sqlite3.Connection) -> bool:
    """Return True if the old wide-format game table exists (has player columns)."""
    info = conn.execute("PRAGMA table_info('game')").fetchall()
    col_names = {row[1] for row in info}
    # If old player columns exist (either raw or display names), we need to migrate
    return bool(col_names & _all_known_player_names())


def _migrate_wide_to_normalized(conn: sqlite3.Connection) -> None:
    """One-time migration from wide game table to normalized schema."""
    info = conn.execute("PRAGMA table_info('game')").fetchall()
    col_names = [row[1] for row in info]
    known = _all_known_player_names()
    player_cols = [c for c in col_names if c in known]

    if not player_cols:
        return

    # Build a mapping from column name → display name
    reverse_map = {v: v for v in PLAYER_COLUMN_MAP.values()}  # display→display
    reverse_map.update({k: v for k, v in PLAYER_COLUMN_MAP.items()})  # raw→display

    # 1. Ensure player table exists and seed players
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS player (
            player_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL UNIQUE,
            display_name TEXT    NOT NULL,
            active       INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS game_result (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            game_overall    INTEGER NOT NULL,
            player_id       INTEGER NOT NULL,
            finish_position INTEGER NOT NULL,
            UNIQUE(game_overall, player_id)
        );
        """
    )

    for col_name in player_cols:
        display = reverse_map.get(col_name, col_name)
        conn.execute(
            "INSERT OR IGNORE INTO player (name, display_name) VALUES (?, ?)",
            [display, display],
        )
    conn.commit()

    # Build player id lookup
    player_rows = conn.execute("SELECT player_id, name FROM player").fetchall()
    player_id_map = {name: pid for pid, name in player_rows}

    # 2. Read all game rows and create game_result entries
    select_cols = ", ".join(f'"{c}"' for c in col_names)
    rows = conn.execute(f"SELECT {select_cols} FROM game ORDER BY game_overall").fetchall()

    for row in rows:
        row_dict = dict(zip(col_names, row))
        game_id = row_dict["game_overall"]
        is_placings = int(row_dict.get("is_placings", 0))
        winner = row_dict.get("winner")

        # Collect participating players for this game
        participants = []
        for col_name in player_cols:
            val = row_dict.get(col_name)
            if val and int(val) > 0:
                display = reverse_map.get(col_name, col_name)
                pid = player_id_map.get(display)
                if pid:
                    participants.append((pid, display, int(val)))

        num_players = len(participants)
        for pid, display, original_pos in participants:
            if is_placings:
                # Real finish positions recorded
                pos = original_pos
            else:
                # No placings: winner gets 1, everyone else gets last
                pos = 1 if display == winner else num_players
            conn.execute(
                "INSERT OR IGNORE INTO game_result (game_overall, player_id, finish_position) VALUES (?, ?, ?)",
                [game_id, pid, pos],
            )
    conn.commit()

    # 3. Rebuild game table without player columns
    keep_cols = [c for c in col_names if c not in player_cols]
    keep_sql = ", ".join(f'"{c}"' for c in keep_cols)
    conn.executescript(
        f"""
        CREATE TABLE game_new (
            game_overall INTEGER PRIMARY KEY,
            season       INTEGER NOT NULL,
            game_date    TEXT    NOT NULL,
            game_number  INTEGER NOT NULL,
            stake        INTEGER NOT NULL,
            winner       TEXT,
            is_placings  INTEGER NOT NULL DEFAULT 0
        );
        INSERT INTO game_new ({keep_sql}) SELECT {keep_sql} FROM game;
        DROP TABLE game;
        ALTER TABLE game_new RENAME TO game;
        """
    )
    conn.commit()


def _ensure_seed_data(conn: sqlite3.Connection) -> None:
    """Bootstrap schema + migrate if needed + seed from CSV if empty."""
    # Check if we need to migrate before touching schema
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "game" in tables and _needs_migration(conn):
        _migrate_wide_to_normalized(conn)

    _ensure_schema(conn)

    count = conn.execute("SELECT COUNT(*) FROM game").fetchone()[0]
    if count:
        return

    # In production the DB should be uploaded, never seeded from CSV
    if os.environ.get("POKER_SKIP_SEED"):
        return

    seed_csv = _seed_csv_path()
    if not seed_csv.exists():
        return

    df = pd.read_csv(seed_csv)
    if df.empty:
        return

    _import_wide_dataframe(conn, df)


def _import_wide_dataframe(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    """Import a wide-format DataFrame (from CSV) into the normalized schema."""
    # Normalize column names
    rename_map = {col: PLAYER_COLUMN_MAP.get(col, col) for col in df.columns}
    df = df.rename(columns=rename_map)

    player_cols = [c for c in df.columns if c not in STANDARD_COLUMNS]

    # Ensure players exist
    for p in player_cols:
        conn.execute(
            "INSERT OR IGNORE INTO player (name, display_name) VALUES (?, ?)",
            [p, p],
        )
    conn.commit()

    player_rows = conn.execute("SELECT player_id, name FROM player").fetchall()
    player_id_map = {name: pid for pid, name in player_rows}

    for _, row in df.iterrows():
        game_data = {col: row[col] for col in STANDARD_COLUMNS if col in row.index}
        game_id = int(game_data["game_overall"])
        is_placings = int(game_data.get("is_placings", 0))
        winner = game_data.get("winner")
        conn.execute(
            """INSERT OR IGNORE INTO game (game_overall, season, game_date, game_number, stake, winner, is_placings)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                game_id,
                int(game_data.get("season", 0)),
                str(game_data.get("game_date", "")),
                int(game_data.get("game_number", 0)),
                int(game_data.get("stake", 0)),
                winner,
                is_placings,
            ],
        )

        # Collect participating players for this game
        participants = []
        for p in player_cols:
            val = row.get(p)
            if pd.notna(val) and int(val) > 0:
                pid = player_id_map.get(p)
                if pid:
                    participants.append((pid, p, int(val)))

        num_players = len(participants)
        for pid, name, original_pos in participants:
            if is_placings:
                pos = original_pos
            else:
                # No placings: winner gets 1, everyone else gets last
                pos = 1 if name == winner else num_players
            conn.execute(
                "INSERT OR IGNORE INTO game_result (game_overall, player_id, finish_position) VALUES (?, ?, ?)",
                [game_id, pid, pos],
            )
    conn.commit()


# ---------------------------------------------------------------------------
# Read helpers  (return long-format DataFrames)
# ---------------------------------------------------------------------------

_GAME_QUERY = """
    SELECT g.game_overall, g.season, g.game_date, g.game_number, g.stake,
           g.winner, g.is_placings,
           p.name AS player, gr.finish_position AS rank
    FROM game g
    JOIN game_result gr ON gr.game_overall = g.game_overall
    JOIN player p ON p.player_id = gr.player_id
"""


def load_games() -> pd.DataFrame:
    with _connect() as conn:
        _ensure_seed_data(conn)
        df = pd.read_sql_query(f"{_GAME_QUERY} ORDER BY g.game_overall, gr.finish_position", conn)
    if not df.empty:
        df["game_date"] = pd.to_datetime(df["game_date"]).dt.date
    return df


def list_games(seasons: list[int] | None = None) -> pd.DataFrame:
    with _connect() as conn:
        _ensure_seed_data(conn)
        if seasons:
            placeholders = ",".join("?" for _ in seasons)
            query = f"{_GAME_QUERY} WHERE g.season IN ({placeholders}) ORDER BY g.game_overall, gr.finish_position"
            df = pd.read_sql_query(query, conn, params=seasons)
        else:
            df = pd.read_sql_query(f"{_GAME_QUERY} ORDER BY g.game_overall, gr.finish_position", conn)
    if not df.empty:
        df["game_date"] = pd.to_datetime(df["game_date"]).dt.date
    return df


def list_games_wide(seasons: list[int] | None = None) -> pd.DataFrame:
    """Return game data in wide format (one row per game) for the history view."""
    with _connect() as conn:
        _ensure_seed_data(conn)
        if seasons:
            placeholders = ",".join("?" for _ in seasons)
            query = f"""
                SELECT g.*, p.name AS player_name, gr.finish_position
                FROM game g
                LEFT JOIN game_result gr ON gr.game_overall = g.game_overall
                LEFT JOIN player p ON p.player_id = gr.player_id
                WHERE g.season IN ({placeholders})
                ORDER BY g.game_overall
            """
            df = pd.read_sql_query(query, conn, params=seasons)
        else:
            query = """
                SELECT g.*, p.name AS player_name, gr.finish_position
                FROM game g
                LEFT JOIN game_result gr ON gr.game_overall = g.game_overall
                LEFT JOIN player p ON p.player_id = gr.player_id
                ORDER BY g.game_overall
            """
            df = pd.read_sql_query(query, conn)

    if df.empty:
        return df

    # Pivot to wide format
    game_cols = ["game_overall", "season", "game_date", "game_number", "stake", "winner", "is_placings"]
    base = df[game_cols].drop_duplicates(subset=["game_overall"])
    if "player_name" in df.columns and df["player_name"].notna().any():
        pivot = df.pivot_table(
            index="game_overall", columns="player_name",
            values="finish_position", aggfunc="first"
        ).reset_index()
        result = base.merge(pivot, on="game_overall", how="left")
    else:
        result = base

    if "game_date" in result.columns:
        result["game_date"] = pd.to_datetime(result["game_date"]).dt.date
    return result.sort_values("game_overall")


def get_metadata() -> dict:
    with _connect() as conn:
        _ensure_seed_data(conn)
        players = [r[0] for r in conn.execute(
            "SELECT name FROM player WHERE active = 1 ORDER BY name"
        ).fetchall()]
        seasons = [r[0] for r in conn.execute(
            "SELECT DISTINCT season FROM game ORDER BY season"
        ).fetchall()]
        latest_season = seasons[-1] if seasons else 1
        next_game_overall = conn.execute(
            "SELECT COALESCE(MAX(game_overall), 0) + 1 FROM game"
        ).fetchone()[0]
    return {
        "players": players,
        "seasons": seasons,
        "latest_season": latest_season,
        "next_game_overall": next_game_overall,
    }


# ---------------------------------------------------------------------------
# Player CRUD
# ---------------------------------------------------------------------------

def list_players() -> list[dict]:
    with _connect() as conn:
        _ensure_seed_data(conn)
        rows = conn.execute(
            "SELECT player_id, name, display_name, active FROM player ORDER BY name"
        ).fetchall()
    return [{"player_id": r[0], "name": r[1], "display_name": r[2], "active": r[3]} for r in rows]


def create_player(name: str, display_name: str) -> int:
    with _connect() as conn:
        _ensure_seed_data(conn)
        cur = conn.execute(
            "INSERT INTO player (name, display_name) VALUES (?, ?)",
            [name, display_name],
        )
        conn.commit()
        return cur.lastrowid


def update_player(player_id: int, updates: dict) -> None:
    allowed = {"name", "display_name", "active"}
    cols = {k: v for k, v in updates.items() if k in allowed}
    if not cols:
        return
    with _connect() as conn:
        _ensure_seed_data(conn)
        assignments = ", ".join(f"{k} = ?" for k in cols)
        values = list(cols.values()) + [player_id]
        conn.execute(f"UPDATE player SET {assignments} WHERE player_id = ?", values)
        conn.commit()


def deactivate_player(player_id: int) -> None:
    update_player(player_id, {"active": 0})


# ---------------------------------------------------------------------------
# Game + result CRUD
# ---------------------------------------------------------------------------

def insert_game(payload: dict) -> int:
    """Insert a game with results.

    payload: {season, game_date, game_number, stake, winner, is_placings,
              results: [{player_id, finish_position}, ...]}
    Also supports legacy flat format for backward compat.
    """
    with _connect() as conn:
        _ensure_seed_data(conn)
        next_id = conn.execute("SELECT COALESCE(MAX(game_overall), 0) + 1 FROM game").fetchone()[0]

        conn.execute(
            """INSERT INTO game (game_overall, season, game_date, game_number, stake, winner, is_placings)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                next_id,
                payload.get("season"),
                str(payload.get("game_date", "")),
                payload.get("game_number"),
                payload.get("stake"),
                payload.get("winner"),
                payload.get("is_placings", 0),
            ],
        )

        results = payload.get("results", [])
        for r in results:
            conn.execute(
                "INSERT INTO game_result (game_overall, player_id, finish_position) VALUES (?, ?, ?)",
                [next_id, r["player_id"], r["finish_position"]],
            )

        conn.commit()
    return int(next_id)


def update_game(game_overall: int, payload: dict) -> None:
    """Update game fields and optionally replace results."""
    with _connect() as conn:
        _ensure_seed_data(conn)
        game_fields = {k: v for k, v in payload.items()
                       if k in ("season", "game_date", "game_number", "stake", "winner", "is_placings") and v is not None}
        if game_fields:
            assignments = ", ".join(f"{k} = ?" for k in game_fields)
            values = list(game_fields.values()) + [game_overall]
            conn.execute(f"UPDATE game SET {assignments} WHERE game_overall = ?", values)

        results = payload.get("results")
        if results is not None:
            conn.execute("DELETE FROM game_result WHERE game_overall = ?", [game_overall])
            for r in results:
                conn.execute(
                    "INSERT INTO game_result (game_overall, player_id, finish_position) VALUES (?, ?, ?)",
                    [game_overall, r["player_id"], r["finish_position"]],
                )
        conn.commit()


def delete_game(game_overall: int) -> None:
    with _connect() as conn:
        _ensure_seed_data(conn)
        conn.execute("DELETE FROM game_result WHERE game_overall = ?", [game_overall])
        conn.execute("DELETE FROM game WHERE game_overall = ?", [game_overall])
        conn.commit()


def load_games_from_csv(csv_path: Path | str, replace: bool = True) -> int:
    path = Path(csv_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(path)
    if df.empty:
        return 0
    with _connect() as conn:
        _ensure_schema(conn)
        if replace:
            conn.execute("DELETE FROM game_result")
            conn.execute("DELETE FROM game")
            conn.commit()
        _import_wide_dataframe(conn, df)
        count = conn.execute("SELECT COUNT(*) FROM game").fetchone()[0]
    return int(count)

