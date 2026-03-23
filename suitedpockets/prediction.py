"""
Next-game win-probability model.

Builds a simple feature-based score per *active* player, converts the scores
to probabilities via softmax, then expresses them as Australian decimal odds.

Features (per player, computed over all available history):
  1. overall_win_rate          – wins / games played
  2. ewma_win_rate             – exponentially-weighted moving average of the
                                 binary win indicator (span = 20 games)
  3. recent_form               – win rate over the last 10 games
  4. heads_up_conversion_rate  – proportion of heads-up appearances that
                                 resulted in a win
  5. runner_up_rate            – finishing 2nd (close-to-winning signal)
  6. first_out_rate            – finishing last (negative signal)
  7. experience_factor         – log(games_played) normalised, rewarding
                                 experience without dominating

Weights were chosen by hand to give sensible odds:
  – EWMA and recent form are weighted highest (recency matters)
  – heads-up conversion is a moderate positive
  – first-out is a moderate negative
  – experience provides a small baseline boost
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Tuneable constants
# ---------------------------------------------------------------------------
EWMA_SPAN = 20          # games look-back for exponential weighting
RECENT_N = 10           # games for "recent form" window
MIN_GAMES = 3           # minimum games before a player gets odds

FEATURE_WEIGHTS = {
    "overall_win_rate":     0.15,
    "ewma_win_rate":        0.30,
    "recent_form":          0.20,
    "hu_conversion":        0.10,
    "runner_up_rate":       0.10,
    "first_out_rate":      -0.10,   # negative = bad signal
    "experience_factor":    0.05,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _softmax(x: np.ndarray) -> np.ndarray:
    """Numerically-stable softmax."""
    e = np.exp(x - np.max(x))
    return e / e.sum()


def _prob_to_decimal_odds(prob: float) -> float:
    """Convert a probability to Australian decimal odds, rounded to $0.05."""
    if prob <= 0:
        return 999.0
    raw = 1.0 / prob
    return round(raw * 20) / 20          # round to nearest 0.05


# ---------------------------------------------------------------------------
# Feature computation
# ---------------------------------------------------------------------------

def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame indexed by *player* with one column per feature.

    ``df`` is the long-format game data returned by
    ``suitedpockets.data.list_games`` (all seasons).
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df = df.loc[df["rank"] > 0].reset_index(drop=True)
    df["is_winner"] = np.where(df["player"] == df["winner"], 1, 0)
    df["game_players"] = df.groupby("game_overall")["player"].transform("count")
    df["is_placings"] = df["is_placings"].fillna(0).astype(int)
    df["is_heads_up"] = np.where((df["is_placings"] == 1) & (df["rank"] <= 2), 1, 0)
    df["is_heads_up_win"] = np.where((df["is_placings"] == 1) & (df["rank"] == 1), 1, 0)
    df["is_first_out"] = np.where((df["is_placings"] == 1) & (df["rank"] == df["game_players"]), 1, 0)
    df["is_runner_up"] = np.where((df["is_placings"] == 1) & (df["rank"] == 2), 1, 0)

    # Sort chronologically within each player
    df = df.sort_values(["player", "game_overall"])

    # --- Per-player aggregations ---
    records = []
    for player, grp in df.groupby("player"):
        n_games = len(grp)
        wins = grp["is_winner"].sum()

        overall_wr = wins / n_games if n_games else 0.0
        ewma_wr = grp["is_winner"].ewm(span=EWMA_SPAN, min_periods=1).mean().iloc[-1]
        recent = grp.tail(RECENT_N)
        recent_form = recent["is_winner"].mean() if len(recent) else 0.0

        hu_total = grp["is_heads_up"].sum()
        hu_wins = grp["is_heads_up_win"].sum()
        hu_conv = hu_wins / hu_total if hu_total > 0 else 0.0

        placing_games = grp["is_placings"].sum()
        runner_up = grp["is_runner_up"].sum() / placing_games if placing_games else 0.0
        first_out = grp["is_first_out"].sum() / placing_games if placing_games else 0.0

        experience = np.log1p(n_games)

        records.append({
            "player": player,
            "games_played": n_games,
            "overall_win_rate": overall_wr,
            "ewma_win_rate": ewma_wr,
            "recent_form": recent_form,
            "hu_conversion": hu_conv,
            "runner_up_rate": runner_up,
            "first_out_rate": first_out,
            "experience_factor": experience,
        })

    features = pd.DataFrame(records).set_index("player")
    return features


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict_next_game(df: pd.DataFrame, active_players: list[str] | None = None) -> list[dict]:
    """Return per-player predictions for the next game.

    Parameters
    ----------
    df : pd.DataFrame
        Long-format game data (all seasons, from ``list_games()``).
    active_players : list[str] | None
        If provided, restrict predictions to these player names.

    Returns
    -------
    list[dict]
        Sorted best-to-worst, each dict contains:
        ``player, probability, decimal_odds, power_score,
          overall_win_rate, ewma_win_rate, recent_form, games_played``
    """
    features = _build_features(df)
    if features.empty:
        return []

    # Filter to active players who have enough history
    if active_players:
        features = features.loc[features.index.isin(active_players)]
    features = features.loc[features["games_played"] >= MIN_GAMES]

    if features.empty:
        return []

    # Normalise experience to [0, 1] range
    exp_col = features["experience_factor"]
    if exp_col.max() > exp_col.min():
        features["experience_factor"] = (exp_col - exp_col.min()) / (exp_col.max() - exp_col.min())
    else:
        features["experience_factor"] = 0.5

    # Compute weighted power score
    score = np.zeros(len(features))
    for feat, weight in FEATURE_WEIGHTS.items():
        score += weight * features[feat].values

    # Softmax → probabilities
    probs = _softmax(score * 5.0)   # temperature scaling for spread

    features = features.copy()
    features["power_score"] = np.round(score, 4)
    features["probability"] = np.round(probs, 4)
    features["decimal_odds"] = [_prob_to_decimal_odds(p) for p in probs]

    # Build output
    out = (
        features
        .reset_index()
        .sort_values("probability", ascending=False)
        [["player", "probability", "decimal_odds", "power_score",
          "overall_win_rate", "ewma_win_rate", "recent_form", "games_played"]]
    )

    # Round display numbers
    for col in ("overall_win_rate", "ewma_win_rate", "recent_form", "power_score"):
        out[col] = out[col].round(3)

    return out.to_dict(orient="records")
