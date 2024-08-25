import pandas as pd
import numpy as np
from suitedpockets.analysis import get_losing_streaks, get_head_to_head, get_player_summary


data = pd.read_csv("./data/complete_stats.csv")
data['game_date'] = pd.to_datetime(data['game_date'], dayfirst=True)

df = pd.melt(data, id_vars=data.columns[0:7], value_vars=data.columns[7:], var_name='player', value_name='rank')

df = df.loc[df['rank'] > 0,].reset_index(drop=True)

df['is_winner'] = np.where(df['player'] == df['winner'], 1, 0)
df['winnings'] = df.groupby('game_overall')['stake'].transform('sum') * df['is_winner']

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

df['is_last_game'] = df.groupby('player')['game_overall'].transform('max') == df['game_overall']



losing_streaks = get_losing_streaks(df)
h2h = get_head_to_head(df, 'Knottorious', 'Nik')

player_summary = get_player_summary(df)