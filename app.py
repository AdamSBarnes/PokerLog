from shiny import App, reactive, render, ui
from pathlib import Path
from suitedpockets.analysis import load_data, get_player_summary, process_data

www_dir = Path(__file__).parent / "www"

FILE_PATH = "data/complete_stats.csv"
raw_data = load_data(FILE_PATH)

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.img(src="logo.png", width="100%"),
        ui.br(),
        ui.input_selectize(
            "seasons",
            "Select Season:",
            {"1": "Season 1 (2023)", "2": "Season 2 (2024)"},
            multiple=True,
            selected=["1", "2"]
        ),
        ui.br(),
        bg="#00040E",
        width=300
    ),
    ui.h1("Suited Pockets: counting cards since 2023"),
    ui.navset_tab(
        ui.nav_panel(
            "Player Summary",
            ui.output_data_frame("player_summary_output")
        ),
        ui.nav_panel(
            "Losing Streaks",
            ui.br()
        ),
        ui.nav_panel(
            "Head to Head",
            ui.br()
        )
    )
)


def server(input, output, session):
    def players():
        return raw_data['player'].unique()

    @reactive.calc
    def processed_data():
        return process_data(raw_data.loc[raw_data['season'].isin([int(i) for i in input.seasons()])])

    @reactive.calc
    def player_summary():
        return get_player_summary(processed_data())

    @output
    @render.data_frame
    def player_summary_output():
        return player_summary()

    @output
    @render.text
    def txt_output():
        return f"Text output: {input.seasons()}"


app = App(app_ui, server, static_assets=www_dir)
