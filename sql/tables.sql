-- Normalized PokerLog schema
-- player:       one row per person
-- game:         one row per poker game
-- game_result:  one row per player per game (finish position)

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

CREATE INDEX IF NOT EXISTS idx_game_result_game ON game_result(game_overall);
CREATE INDEX IF NOT EXISTS idx_game_result_player ON game_result(player_id);
CREATE INDEX IF NOT EXISTS idx_game_season ON game(season);
