import pandas as pd
import numpy as np

pd.options.mode.chained_assignment = None


def load_data(path: str) -> pd.DataFrame:
    data = pd.read_csv(path)
    data['game_date'] = pd.to_datetime(data['game_date'], dayfirst=True)

    df = pd.melt(data, id_vars=data.columns[0:7], value_vars=data.columns[7:], var_name='player', value_name='rank')

    df = df.loc[df['rank'] > 0,].reset_index(drop=True)

    df['is_winner'] = np.where(df['player'] == df['winner'], 1, 0)
    df['winnings'] = df.groupby('game_overall')['stake'].transform('sum') * df['is_winner']
    df['is_last_game'] = df.groupby('player')['game_overall'].transform('max') == df['game_overall']

    return df


def process_data(input_df: pd.DataFrame) -> pd.DataFrame:
    df = input_df
    # cumulative sum of wins by player
    df['win_count'] = df.groupby('player')['is_winner'].cumsum()

    df['all_time_games_played'] = df.groupby('player')['game_overall'].transform('cumcount') + 1
    df['all_time_winnings'] = df.groupby('player')['winnings'].cumsum()
    df['all_time_costs'] = df.groupby('player')['stake'].cumsum()

    df['all_time_return'] = np.where(
        df['all_time_games_played'] < 5,
        np.nan,
        np.round(df['all_time_winnings'] / df['all_time_costs'], 2)
    )

    df['season_games_played'] = df.groupby(['player', 'season'])['game_overall'].transform('cumcount') + 1
    df['season_winnings'] = df.groupby(['player', 'season'])['winnings'].cumsum()
    df['season_costs'] = df.groupby(['player', 'season'])['stake'].cumsum()
    df['season_return'] = np.where(
        df['season_games_played'] < 5,
        np.nan,
        np.round(df['season_winnings'] / df['season_costs'], 2)
    )
    return df


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
