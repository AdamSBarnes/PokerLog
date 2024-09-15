from shiny import App, reactive, render, ui
from pathlib import Path
from suitedpockets.analysis import load_data, get_player_summary, process_data, get_losing_streaks
from suitedpockets.plot import form_plot, plot_losing_streaks
from shinywidgets import output_widget, render_widget
from shinyswatch import theme

www_dir = Path(__file__).parent / "www"

FILE_PATH = "data/complete_stats.csv"
raw_data = load_data(FILE_PATH)

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.img(src="logo2.jpeg", width="100%"),
        ui.br(),
        ui.input_selectize(
            "seasons",
            "Select Season:",
            {"1": "Season 1 (2023)", "2": "Season 2 (2024)"},
            multiple=True,
            selected=["1", "2"]
        ),
        ui.br(),
        bg="#013356",
        width=300
    ),
    ui.navset_tab(
        ui.nav_panel(
            "Player Summary",
            ui.layout_columns(
                ui.card(
                    ui.card_header("Performance Summary"),
                    ui.output_data_frame("player_summary_output")
                ),
                ui.card(
                    ui.card_header("Return on Investment"),
                    output_widget("form_plot_out")
                )
            )
        ),
        ui.nav_panel(
            "Losing Streaks",
            ui.layout_columns(
                ui.card(
                    ui.card_header("Longest Losing Streaks"),
                    output_widget("plot_losing_streaks_out")
                ),
                ui.card(
                    ui.card_header("Losing Streaks"),
                    ui.output_data_frame("losing_streaks_output")
                )
            )
        ),
        ui.nav_panel(
            "Head to Head",
            ui.br()
        )
    ),
    #theme=theme.superhero
)


def server(input, output, session):
    def players():
        return raw_data['player'].unique()

    @reactive.calc
    def processed_data():
        return process_data(raw_data.loc[raw_data['season'].isin([int(i) for i in input.seasons()])])

    @reactive.calc
    def losing_streaks():
        return get_losing_streaks(processed_data())

    @output
    @render.data_frame
    def losing_streaks_output():
        return losing_streaks().drop(['streak_rank', 'streak_name'], axis=1)

    @render_widget
    def plot_losing_streaks_out():
        return plot_losing_streaks(get_losing_streaks(processed_data(), n=10))

    @render_widget
    def form_plot_out():
        return form_plot(processed_data())

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
