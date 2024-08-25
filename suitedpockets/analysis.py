import pandas as pd
import numpy as np


def get_losing_streaks(df: pd.DataFrame) -> pd.DataFrame:
    losing_streaks = df.groupby(['player', 'win_count']).agg(
        streak_start_date=('game_date', 'min'),
        streak_start_game=('game_overall', 'min'),
        streak_end_date=('game_date', 'max'),
        streak_end_game=('game_overall', 'max'),
        streak_length=('game_overall', 'size'),
        is_active=('is_last_game', 'sum')
    ).reset_index()

    losing_streaks['streak_length'] = losing_streaks['streak_length'] - 1
    losing_streaks = losing_streaks.drop('win_count', axis=1)

    return losing_streaks.loc[losing_streaks['streak_length'] > 0]


def get_head_to_head(df: pd.DataFrame, player_one: str, player_two: str) -> pd.DataFrame:
    df_p1 = df.loc[df['player'] == player_one]
    df_p2 = df.loc[df['player'] == player_two]

    merged = pd.concat([
        df_p1.loc[df_p1['game_overall'].isin(df_p2['game_overall'])],
        df_p2.loc[df_p2['game_overall'].isin(df_p1['game_overall'])]
    ], ignore_index=False)

    stats = merged.groupby('player').agg(
        winnings=('winnings', 'sum'),
        wins=('is_winner', 'sum'),
        played=('game_overall', 'count')
    )

    stats['dominance'] = np.round(stats['wins'] / stats['wins'].sum(), 2)

    return stats


def get_player_summary(input_df: pd.DataFrame) -> pd.DataFrame:
    summary_ten = (
        input_df
            .loc[input_df['stake'] == 10]
            .groupby('player').agg(
                wins_ten=('is_winner', 'sum'),
                played_ten=('game_overall', 'count')
            )
    )

    summary_ten['win_rate_ten'] = np.round(summary_ten['wins_ten'] / summary_ten['played_ten'],2)

    summary = input_df.groupby('player').agg(
        winnings=('winnings', 'sum'),
        wins=('is_winner', 'sum'),
        played=('game_overall', 'count')
    )
    summary['win_rate'] = np.round(summary['wins'] / summary['played'],2)


    return summary.merge(summary_ten, on='player', how='left').reset_index(drop=False)
