import pandas as pd
import numpy as np

pd.options.mode.chained_assignment = None

# data['game_date'] = pd.to_datetime(data['game_date'], dayfirst=True).dt.date.astype(str)


def process_data(input_df: pd.DataFrame) -> pd.DataFrame:
    df = pd.melt(input_df, id_vars=input_df.columns[0:7], value_vars=input_df.columns[7:], var_name='player', value_name='rank')

    df = df.loc[df['rank'] > 0,].reset_index(drop=True)

    df['is_winner'] = np.where(df['player'] == df['winner'], 1, 0)
    df['winnings'] = df.groupby('game_overall')['stake'].transform('sum') * df['is_winner']
    df['is_last_game'] = df.groupby('player')['game_overall'].transform('max') == df['game_overall']

    # cumulative sum of wins by player
    df['win_count'] = df.groupby('player')['is_winner'].cumsum()
    df['game_players'] = df.groupby('game_overall')['player'].transform('count')

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

    df['is_heads_up'] = np.where(np.logical_and(df['is_placings'] == 1, df['rank'] <= 2), 1, 0)
    df['is_heads_up_win'] = np.where(np.logical_and(df['is_placings'] == 1, df['rank'] == 1), 1, 0)

    df['is_first_out'] = np.where(np.logical_and(df['is_placings'] == 1, df['rank'] == df['game_players']),1,0)

    return df


def get_losing_streaks(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    losing_streaks = df.groupby(['player', 'win_count']).agg(
        streak_start_date=('game_date', 'min'),
        streak_start_game=('game_overall', 'min'),
        streak_end_date=('game_date', 'max'),
        streak_end_game=('game_overall', 'max'),
        streak_length=('game_overall', 'size'),
        streak_loss=('stake', 'sum'),
        is_active=('is_last_game', 'sum')
    ).reset_index()

    losing_streaks['streak_loss'] = losing_streaks['streak_loss'].apply(lambda x: f'${x:,.0f}')

    # convert to date from datetime
    #losing_streaks['streak_end_date'] = losing_streaks['streak_end_date'].dt.date.astype(str)
    #losing_streaks['streak_start_date'] = losing_streaks['streak_start_date'].dt.date.astype(str)

    losing_streaks['streak_length'] = losing_streaks['streak_length'] - 1
    losing_streaks = losing_streaks.drop('win_count', axis=1)

    losing_streaks = losing_streaks.loc[losing_streaks['streak_length'] > 0]

    losing_streaks = losing_streaks.sort_values(by='streak_length', ascending=False).reset_index(drop=True).iloc[0:n, :]
    losing_streaks['streak_rank'] = losing_streaks.index + 1
    losing_streaks['streak_name'] = losing_streaks['player'] + ': ' + losing_streaks['streak_length'].astype(
        str) + ' games'

    return losing_streaks


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

    summary_ten['win_rate_ten'] = np.round(summary_ten['wins_ten'] / summary_ten['played_ten'], 2)

    summary_ten = summary_ten.drop('played_ten', axis=1)

    summary = input_df.groupby('player').agg(
        costs=('stake', 'sum'),
        winnings=('winnings', 'sum'),
        wins=('is_winner', 'sum'),
        played=('game_overall', 'count'),
        heads_up=('is_heads_up', 'sum'),
        heads_up_win=('is_heads_up_win', 'sum'),
        placing_games=('is_placings', 'sum'),
        first_out=('is_first_out', 'sum')
    )

    summary['heads_up_conversion_rate'] = (summary['heads_up_win'] / summary['heads_up']).apply(
        lambda x: f'{x * 100:.0f}%')

    summary['first_out_rate'] = (summary['first_out'] / summary['placing_games']).apply(
        lambda x: f'{x * 100:.0f}%')

    # days since win
    last_wins = input_df.loc[input_df['is_winner'] == 1].groupby('player')['game_date'].max().reset_index().rename(
        columns={'game_date': 'last_win_date'})

    #last_wins['last_win_date'] = last_wins['last_win_date'].dt.date.astype(str)

    summary['win_rate'] = np.round(summary['wins'] / summary['played'], 2)
    summary['return_rate'] = np.round(summary['winnings'] / summary['costs'], 2).apply(lambda x: f'${x:,.2f}')

    summary['net_position'] = (summary['winnings'] - summary['costs']).apply(lambda x: f'${x:,.0f}')

    summary['costs'] = summary['costs'].apply(lambda x: f'${x:,.0f}')
    summary['winnings'] = summary['winnings'].apply(lambda x: f'${x:,.0f}')
    summary['win_rate'] = summary['win_rate'].apply(lambda x: f'{x * 100:.0f}%')

    summary = summary.merge(summary_ten, on='player', how='left').reset_index(drop=False).sort_values(by='return_rate',
                                                                                                      ascending=False)
    summary = summary.merge(last_wins, on='player', how='left').reset_index(drop=False)
    summary = summary[
        ['player', 'costs', 'winnings', 'net_position', 'wins', 'wins_ten', 'win_rate', 'return_rate', 'last_win_date',
         'heads_up_conversion_rate', 'first_out_rate']
    ]

    return summary.set_index('player').transpose().reset_index(drop=False).rename(columns={'index': 'statistic'})