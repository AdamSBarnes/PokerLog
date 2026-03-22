from datetime import date

from backend.analytics import game_history, metadata, player_summary, roi_series
from suitedpockets.data import delete_game, insert_game


def main() -> None:
    meta = metadata()
    seasons = meta.get("seasons", [])
    players = meta.get("players", [])
    assert seasons, "No seasons found in metadata"
    assert players, "No players found in metadata"

    summary = player_summary(seasons)
    assert summary, "Player summary should not be empty"

    series = roi_series(seasons)
    assert series, "ROI series should not be empty"

    games = game_history(seasons)
    assert games, "Game history should not be empty"

    payload = {
        "season": seasons[-1],
        "game_date": date.today(),
        "game_number": 99,
        "stake": 10,
        "winner": players[0],
        "is_placings": 1,
    }
    for idx, player in enumerate(players, start=1):
        payload[player] = idx

    new_id = insert_game(payload)
    delete_game(new_id)

    print("smoketest ok")


if __name__ == "__main__":
    main()

