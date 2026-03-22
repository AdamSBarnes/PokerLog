from datetime import date

from backend.analytics import game_history, metadata, player_summary, roi_series
from suitedpockets.data import delete_game, insert_game, list_players, create_player


def main() -> None:
    meta = metadata()
    seasons = meta.get("seasons", [])
    players_list = list_players()

    # Ensure at least one player exists for the test
    if not players_list:
        create_player("TestPlayer", "Test Player")
        players_list = list_players()

    player_names = meta.get("players", [])

    if seasons and player_names:
        summary = player_summary(seasons)
        assert summary, "Player summary should not be empty"

        series = roi_series(seasons)
        assert series, "ROI series should not be empty"

        games = game_history(seasons)
        assert games, "Game history should not be empty"

    # Test insert + delete with normalized structure
    test_season = seasons[-1] if seasons else 1
    results = [{"player_id": p["player_id"], "finish_position": idx}
               for idx, p in enumerate(players_list[:3], start=1)]

    winner_name = players_list[0]["name"] if players_list else None

    payload = {
        "season": test_season,
        "game_date": date.today(),
        "game_number": 99,
        "stake": 10,
        "winner": winner_name,
        "is_placings": 1,
        "results": results,
    }

    new_id = insert_game(payload)
    delete_game(new_id)

    print("smoketest ok")


if __name__ == "__main__":
    main()
