from suitedpockets.analysis import get_losing_streaks, get_head_to_head, get_player_summary, load_data, process_data

FILE_PATH = "./data/complete_stats.csv"


data = load_data(FILE_PATH)

processed_data = process_data(data)

losing_streaks = get_losing_streaks(processed_data)
h2h = get_head_to_head(processed_data, 'Knottorious', 'Nik')

player_summary = get_player_summary(processed_data)