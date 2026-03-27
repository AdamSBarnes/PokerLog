from typing import Iterable

import numpy as np
import pandas as pd

from suitedpockets.analysis import get_head_to_head, get_losing_streaks, get_player_summary, process_data
from suitedpockets.data import get_metadata, list_games, list_games_wide, list_players
from suitedpockets.prediction import predict_next_game


def _season_list(seasons: Iterable[int] | None) -> list[int] | None:
    if seasons is None:
        return None
    return [int(s) for s in seasons]


def metadata() -> dict:
    return get_metadata()


def game_history(seasons: Iterable[int] | None) -> list[dict]:
    df = list_games_wide(_season_list(seasons))
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


def predictions() -> list[dict]:
    """Predict win probabilities for the next game using all historical data."""
    df = list_games(None)  # all seasons
    active = [p["name"] for p in list_players() if p.get("active")]
    return predict_next_game(df, active_players=active)


# ---------------------------------------------------------------------------
# Player profile deep-dive
# ---------------------------------------------------------------------------

def player_profile(player_name: str) -> dict:
    """Return a comprehensive profile for a single player."""
    df = list_games(None)  # all seasons
    if df.empty:
        return {}

    processed = process_data(df)
    pdf = processed[processed["player"] == player_name].copy()
    if pdf.empty:
        return {}

    pdf = pdf.sort_values("game_overall")

    # ── Key stats ──────────────────────────────────────────────
    total_played = len(pdf)
    total_wins = int(pdf["is_winner"].sum())
    total_costs = int(pdf["stake"].sum())
    total_winnings = int(pdf["winnings"].sum())
    net_position = total_winnings - total_costs
    win_rate = round(total_wins / total_played, 3) if total_played else 0
    return_rate = round(total_winnings / total_costs, 3) if total_costs else 0

    placing_games = int(pdf["is_placings"].sum())
    hu_total = int(pdf["is_heads_up"].sum())
    hu_wins = int(pdf["is_heads_up_win"].sum())
    hu_conv = round(hu_wins / hu_total, 3) if hu_total else 0
    first_out_count = int(pdf["is_first_out"].sum())
    first_out_rate = round(first_out_count / placing_games, 3) if placing_games else 0
    runner_up_count = int(pdf["is_runner_up"].sum())
    runner_up_rate = round(runner_up_count / placing_games, 3) if placing_games else 0

    # Average finish position (lower is better)
    avg_finish = round(float(pdf["rank"].mean()), 2) if total_played else 0

    # Wins in $10 games
    ten_games = pdf[pdf["stake"] == 10]
    wins_ten = int(ten_games["is_winner"].sum()) if not ten_games.empty else 0

    last_win_rows = pdf[pdf["is_winner"] == 1]
    last_win_date = str(last_win_rows["game_date"].max()) if not last_win_rows.empty else None

    key_stats = {
        "played": total_played,
        "wins": total_wins,
        "wins_ten": wins_ten,
        "costs": total_costs,
        "winnings": total_winnings,
        "net_position": net_position,
        "win_rate": win_rate,
        "return_rate": return_rate,
        "avg_finish": avg_finish,
        "heads_up_appearances": hu_total,
        "heads_up_wins": hu_wins,
        "heads_up_conversion": hu_conv,
        "first_out_count": first_out_count,
        "first_out_rate": first_out_rate,
        "runner_up_count": runner_up_count,
        "runner_up_rate": runner_up_rate,
        "last_win_date": last_win_date,
    }

    # ── Personal ROI series ────────────────────────────────────
    roi_data = pdf[["game_overall", "all_time_return"]].copy()
    roi_data.columns = ["game_overall", "roi"]
    personal_roi = roi_data.to_dict(orient="records")

    # ── Recent form (last 10 games, W/L indicators) ────────────
    recent = pdf.tail(10)
    recent_form = []
    for _, row in recent.iterrows():
        recent_form.append({
            "game_overall": int(row["game_overall"]),
            "game_date": str(row["game_date"]),
            "won": bool(row["is_winner"]),
            "finish_position": int(row["rank"]),
            "players_in_game": int(row["game_players"]),
            "stake": int(row["stake"]),
        })

    # ── Head-to-head vs every other player ─────────────────────
    all_players = processed["player"].unique()
    h2h_records = []
    for opponent in all_players:
        if opponent == player_name:
            continue
        h2h = get_head_to_head(processed, player_name, opponent)
        if h2h.empty or player_name not in h2h.index:
            continue
        p_row = h2h.loc[player_name]
        o_row = h2h.loc[opponent] if opponent in h2h.index else None
        shared_games = int(p_row["played"])
        if shared_games == 0:
            continue
        my_wins = int(p_row["wins"])
        opp_wins = int(o_row["wins"]) if o_row is not None else 0
        h2h_records.append({
            "opponent": opponent,
            "games_together": shared_games,
            "my_wins": my_wins,
            "opp_wins": opp_wins,
            "dominance": round(float(p_row["dominance"]), 3) if (my_wins + opp_wins) > 0 else 0.5,
        })
    h2h_records.sort(key=lambda x: x["dominance"], reverse=True)

    # ── Season breakdown + best/worst season ───────────────────
    season_stats = []
    for season, sdf in pdf.groupby("season"):
        s_played = len(sdf)
        s_wins = int(sdf["is_winner"].sum())
        s_costs = int(sdf["stake"].sum())
        s_winnings = int(sdf["winnings"].sum())
        s_net = s_winnings - s_costs
        s_roi = round(s_winnings / s_costs, 3) if s_costs else 0
        s_wr = round(s_wins / s_played, 3) if s_played else 0
        season_stats.append({
            "season": int(season),
            "played": s_played,
            "wins": s_wins,
            "costs": s_costs,
            "winnings": s_winnings,
            "net": s_net,
            "roi": s_roi,
            "win_rate": s_wr,
        })

    best_season = max(season_stats, key=lambda x: x["roi"]) if season_stats else None
    worst_season = min(season_stats, key=lambda x: x["roi"]) if season_stats else None

    # ── Achievements / badges ──────────────────────────────────
    badges = _compute_badges(processed, player_name, pdf, total_played,
                             total_wins, win_rate, return_rate, hu_conv,
                             first_out_rate, runner_up_rate, season_stats)

    # ── Strengths & weaknesses ─────────────────────────────────
    strengths, weaknesses = _compute_strengths_weaknesses(
        processed, player_name, win_rate, return_rate, hu_conv,
        first_out_rate, runner_up_rate, avg_finish, recent_form
    )

    return {
        "player": player_name,
        "key_stats": key_stats,
        "personal_roi": personal_roi,
        "recent_form": recent_form,
        "head_to_head": h2h_records,
        "season_breakdown": season_stats,
        "best_season": best_season,
        "worst_season": worst_season,
        "badges": badges,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


def _compute_badges(processed, player_name, pdf, total_played,
                     total_wins, win_rate, return_rate, hu_conv,
                     first_out_rate, runner_up_rate, season_stats):
    """Compute a list of achievement badges for the player."""
    badges = []

    # --- League-wide comparisons ---
    all_stats = {}
    for p, grp in processed.groupby("player"):
        all_stats[p] = {
            "played": len(grp),
            "wins": int(grp["is_winner"].sum()),
            "winnings": int(grp["winnings"].sum()),
            "costs": int(grp["stake"].sum()),
        }
        pg = int(grp["is_placings"].sum())
        hu = int(grp["is_heads_up"].sum())
        hu_w = int(grp["is_heads_up_win"].sum())
        all_stats[p]["win_rate"] = all_stats[p]["wins"] / all_stats[p]["played"] if all_stats[p]["played"] else 0
        all_stats[p]["roi"] = all_stats[p]["winnings"] / all_stats[p]["costs"] if all_stats[p]["costs"] else 0
        all_stats[p]["hu_conv"] = hu_w / hu if hu else 0
        all_stats[p]["first_out_rate"] = int(grp["is_first_out"].sum()) / pg if pg else 0

    # Most games played
    most_played = max(all_stats.values(), key=lambda x: x["played"])["played"]
    if total_played == most_played:
        badges.append({"icon": "🏋️", "title": "Iron Man", "desc": "Most games played in the league"})

    # Highest win rate (min 10 games)
    eligible = {p: s for p, s in all_stats.items() if s["played"] >= 10}
    if eligible:
        best_wr = max(eligible.values(), key=lambda x: x["win_rate"])["win_rate"]
        if win_rate == best_wr and total_played >= 10:
            badges.append({"icon": "🎯", "title": "Sharpshooter", "desc": "Highest win rate in the league"})

    # Highest ROI (min 10 games)
    if eligible:
        best_roi = max(eligible.values(), key=lambda x: x["roi"])["roi"]
        if return_rate == best_roi and total_played >= 10:
            badges.append({"icon": "💰", "title": "Money Bags", "desc": "Best return on investment"})

    # Best heads-up conversion (min 5 HU)
    hu_eligible = {p: s for p, s in all_stats.items() if s.get("hu_conv", 0) > 0}
    if hu_eligible and hu_conv > 0:
        best_hu = max(hu_eligible.values(), key=lambda x: x["hu_conv"])["hu_conv"]
        if hu_conv == best_hu:
            badges.append({"icon": "🤝", "title": "Heads-Up Hero", "desc": "Best heads-up conversion rate"})

    # --- Personal milestones ---
    if total_wins >= 50:
        badges.append({"icon": "👑", "title": "Half Century", "desc": "50+ career wins"})
    elif total_wins >= 25:
        badges.append({"icon": "🏆", "title": "Quarter Century", "desc": "25+ career wins"})
    elif total_wins >= 10:
        badges.append({"icon": "⭐", "title": "Double Digits", "desc": "10+ career wins"})

    if total_played >= 100:
        badges.append({"icon": "💯", "title": "Centurion", "desc": "100+ games played"})
    elif total_played >= 50:
        badges.append({"icon": "🎲", "title": "Regular", "desc": "50+ games played"})

    # Profitable overall
    if return_rate >= 1.0:
        badges.append({"icon": "📈", "title": "In The Green", "desc": "Career ROI at or above break-even"})
    else:
        badges.append({"icon": "📉", "title": "Paying Dues", "desc": "Career ROI below break-even"})

    # Win rate > 20%
    if win_rate >= 0.20 and total_played >= 10:
        badges.append({"icon": "🔥", "title": "Hot Hand", "desc": "Win rate of 20%+"})

    # High heads-up conversion
    if hu_conv >= 0.6 and int(pdf["is_heads_up"].sum()) >= 5:
        badges.append({"icon": "🎰", "title": "Closer", "desc": "60%+ heads-up conversion rate"})

    # Survived a lot (low first-out rate)
    if first_out_rate <= 0.10 and int(pdf["is_placings"].sum()) >= 10:
        badges.append({"icon": "🛡️", "title": "Survivor", "desc": "First-out rate under 10%"})

    # Bridesmaid (high runner-up rate)
    if runner_up_rate >= 0.20 and int(pdf["is_placings"].sum()) >= 10:
        badges.append({"icon": "🥈", "title": "Always The Bridesmaid", "desc": "Runner-up rate of 20%+"})

    # Season champion (best ROI in any season with 5+ games)
    for ss in season_stats:
        if ss["played"] >= 5 and ss["roi"] >= 1.5:
            badges.append({
                "icon": "🏅",
                "title": f"Season {ss['season']} Dominator",
                "desc": f"ROI of ${ss['roi']:.2f} in season {ss['season']}"
            })
            break  # Only award once

    # Recent hot streak: won 3+ of last 10
    recent_wins = sum(1 for _, r in pdf.tail(10).iterrows() if r["is_winner"])
    if recent_wins >= 3:
        badges.append({"icon": "🌟", "title": "On Fire", "desc": f"Won {recent_wins} of last 10 games"})

    # Big spender (played 20+ games at $20+ stake)
    big_games = pdf[pdf["stake"] >= 20]
    if len(big_games) >= 20:
        badges.append({"icon": "💎", "title": "High Roller", "desc": "20+ games at $20+ stakes"})

    return badges


def _compute_strengths_weaknesses(processed, player_name, win_rate, return_rate,
                                   hu_conv, first_out_rate, runner_up_rate,
                                   avg_finish, recent_form):
    """Compute strengths and weaknesses relative to the league."""
    # Get league averages
    league = {}
    for p, grp in processed.groupby("player"):
        pg = int(grp["is_placings"].sum())
        hu = int(grp["is_heads_up"].sum())
        hu_w = int(grp["is_heads_up_win"].sum())
        league[p] = {
            "win_rate": grp["is_winner"].sum() / len(grp) if len(grp) else 0,
            "roi": grp["winnings"].sum() / grp["stake"].sum() if grp["stake"].sum() else 0,
            "hu_conv": hu_w / hu if hu else 0,
            "first_out_rate": int(grp["is_first_out"].sum()) / pg if pg else 0,
            "runner_up_rate": int(grp["is_runner_up"].sum()) / pg if pg else 0,
            "avg_finish": grp["rank"].mean(),
        }

    avg_wr = np.mean([v["win_rate"] for v in league.values()])
    avg_roi = np.mean([v["roi"] for v in league.values()])
    avg_hu = np.mean([v["hu_conv"] for v in league.values() if v["hu_conv"] > 0] or [0])
    avg_fo = np.mean([v["first_out_rate"] for v in league.values()])
    avg_ru = np.mean([v["runner_up_rate"] for v in league.values()])
    avg_af = np.mean([v["avg_finish"] for v in league.values()])

    strengths = []
    weaknesses = []

    # Win rate
    if win_rate > avg_wr * 1.15:
        strengths.append(f"Win rate ({win_rate*100:.0f}%) is above league average ({avg_wr*100:.0f}%)")
    elif win_rate < avg_wr * 0.85:
        weaknesses.append(f"Win rate ({win_rate*100:.0f}%) is below league average ({avg_wr*100:.0f}%)")

    # ROI
    if return_rate > avg_roi * 1.15:
        strengths.append(f"ROI (${return_rate:.2f}) beats the league average (${avg_roi:.2f})")
    elif return_rate < avg_roi * 0.85:
        weaknesses.append(f"ROI (${return_rate:.2f}) trails the league average (${avg_roi:.2f})")

    # Heads-up
    if hu_conv > avg_hu * 1.15:
        strengths.append(f"Strong closer — {hu_conv*100:.0f}% heads-up conversion (avg {avg_hu*100:.0f}%)")
    elif hu_conv < avg_hu * 0.85 and hu_conv > 0:
        weaknesses.append(f"Heads-up conversion ({hu_conv*100:.0f}%) below average ({avg_hu*100:.0f}%)")

    # First out
    if first_out_rate < avg_fo * 0.85:
        strengths.append(f"Rarely first out ({first_out_rate*100:.0f}% vs avg {avg_fo*100:.0f}%)")
    elif first_out_rate > avg_fo * 1.15:
        weaknesses.append(f"First out too often ({first_out_rate*100:.0f}% vs avg {avg_fo*100:.0f}%)")

    # Average finish
    if avg_finish < avg_af * 0.9:
        strengths.append(f"Avg finish position {avg_finish:.1f} is better than league avg {avg_af:.1f}")
    elif avg_finish > avg_af * 1.1:
        weaknesses.append(f"Avg finish position {avg_finish:.1f} is worse than league avg {avg_af:.1f}")

    # Recent form
    recent_wins = sum(1 for r in recent_form if r["won"])
    if recent_wins >= 3:
        strengths.append(f"Hot recent form — {recent_wins} wins in last {len(recent_form)} games")
    elif recent_wins == 0 and len(recent_form) >= 5:
        weaknesses.append(f"Cold streak — no wins in last {len(recent_form)} games")

    # Runner-up (could be a positive indicator of deep runs)
    if runner_up_rate > avg_ru * 1.3:
        weaknesses.append(f"Frequently runner-up ({runner_up_rate*100:.0f}%) — converting deep runs to wins is an opportunity")

    return strengths, weaknesses


