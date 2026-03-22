from typing import Iterable

import pandas as pd

from suitedpockets.analysis import get_losing_streaks, get_player_summary, process_data
from suitedpockets.data import get_metadata, list_games


def _season_list(seasons: Iterable[int] | None) -> list[int] | None:
    if seasons is None:
        return None
    return [int(s) for s in seasons]


def metadata() -> dict:
    return get_metadata()


def game_history(seasons: Iterable[int] | None) -> list[dict]:
    df = list_games(_season_list(seasons))
    if not df.empty:
        df["game_date"] = pd.to_datetime(df["game_date"]).dt.date.astype(str)
    return df.to_dict(orient="records")


def player_summary(seasons: Iterable[int] | None) -> list[dict]:
    df = list_games(_season_list(seasons))
    processed = process_data(df)
    summary = get_player_summary(processed)
    return summary.to_dict(orient="records")


def losing_streaks(seasons: Iterable[int] | None, n: int, active_only: bool) -> list[dict]:
    df = list_games(_season_list(seasons))
    processed = process_data(df)
    streaks = get_losing_streaks(processed, n=n, filter_active=active_only)
    return streaks.to_dict(orient="records")


def roi_series(seasons: Iterable[int] | None) -> list[dict]:
    df = list_games(_season_list(seasons))
    processed = process_data(df)
    series = processed[["game_overall", "player", "all_time_return"]]
    return series.to_dict(orient="records")

