from shiny import App, reactive, render, ui
from pathlib import Path
from suitedpockets.data import load_games
from suitedpockets.analysis import get_player_summary, process_data, get_losing_streaks
from suitedpockets.plot import form_plot, plot_losing_streaks
from suitedpockets.format import highlight_negative_return
from shinywidgets import output_widget, render_widget

www_dir = Path(__file__).parent / "www"

game_data = load_games()

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
                    ui.output_data_frame("player_summary_output"),
                ),
                ui.card(
                    ui.card_header("Metric Definitions"),
                    ui.p(
                        ui.strong("* Played"), " is the number of games played.",
                        ui.br(),
                        ui.strong("* Costs"), " is the sum of all entry fees.",
                        ui.br(),
                        ui.strong("* Winnings"), " is total won. Settled at end of season(s).",
                        ui.br(),
                        ui.strong("* Net Position"), " is Winnings less Costs.",
                        ui.br(),
                        ui.strong("* Wins"), " is the number of wins across all games.",
                        ui.br(),
                        ui.strong("* Wins Ten"), " is the number of wins in $10 games.",
                        ui.br(),
                        ui.strong("* Win Rate"), " is Wins divided by Played.",
                        ui.br(),
                        ui.strong("* Return Rate (ROI)"), " is Winnings divided by Costs",
                        ui.br(),
                        ui.strong("* Last Win Date"), " is the date of the last win.",
                        ui.br(),
                        ui.strong("* Heads Up Conversion Rate"), " rate at which final two results in a win.",
                        ui.br(),
                        ui.strong("* First Out Rate"), " rate at which player is knocked out first.",
                        ui.br(),
                        ui.p(
                            "Places only tracked since game number 94, early in season two. "
                            "All stats are filtered by the season filter in the sidebar.",
                            ui.br(),
                            ui.br(),
                            "Overall winner is determined within a season based on Return Rate."
                        )

                    )
                ),
                ui.card(
                    ui.card_header("Return on Investment"),
                    output_widget("form_plot_out")
                ),
                col_widths=[6, 6, 12]
            )
        ),
        ui.nav_panel(
            "Losing Streaks",
            ui.layout_columns(
                ui.card(
                    ui.card_header("Longest Losing Streaks"),
                    output_widget("plot_losing_streaks_out"),
                ),
                ui.card(
                    ui.card_header("Current Losing Streaks"),
                    output_widget("plot_current_losing_streaks_out"),
                ),
                ui.card(
                    ui.card_header("Losing Streaks"),
                    ui.output_data_frame("losing_streaks_output")
                ),
                col_widths=[6, 6, 6]
            )
        ),
        # ui.nav_panel(
        #     "Head to Head",
        #     ui.layout_columns(
        #         ui.card(
        #             ui.output_ui("p1_pick"),
        #             ui.output_ui("p2_pick")
        #         )
        #     ),
        # ),
        ui.nav_panel(
            "Game History",
            ui.output_data_frame("raw_result_output")
        )
    )
)


def server(input, output, session):
    @render.ui
    def p1_pick():
        return ui.input_select(
            id="input_p1",
            label="Player One",
            choices=[p for p in players()],
            selected=players()[0]
        )

    @render.ui
    def p2_pick():
        return ui.input_select(
            id="input_p2",
            label="Player Two",
            choices=[p for p in players()],
            selected=players()[1]
        )

    @reactive.calc
    def processed_data():
        return process_data(game_data.loc[game_data['season'].isin([int(i) for i in input.seasons()])])

    @reactive.calc
    def players():
        return processed_data()['player'].unique()

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
    def plot_current_losing_streaks_out():
        return plot_losing_streaks(get_losing_streaks(processed_data(), n=9999999, filter_active=True))

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

    @output
    @render.data_frame
    def raw_result_output():
        df = game_data.loc[game_data['season'].isin([int(i) for i in input.seasons()])]
        df['game_date'] = df['game_date'].astype('str')
        df = df.sort_values('game_overall', ascending=False)
        return df


app = App(app_ui, server, static_assets=www_dir)
