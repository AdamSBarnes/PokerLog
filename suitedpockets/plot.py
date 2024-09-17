import pandas as pd
import plotly.express as px

color_palette = {
    'Knottorious': '#99B898',   # Cyan Blue
    'Cedric': '#FECEAB',   # Coral
    'Dale-O': '#FF847C',   # Lime Green
    'Nik': '#E84A5F',   # Goldenrod
    'El-Craigo': '#2A363B'    # Orchid
}

def plot_losing_streaks(df):
    fig = px.bar(
        df,
        x='streak_length',
        y='streak_rank',
        orientation='h',
        color='player',
        text='streak_name',
        template='plotly_white',
        #color_discrete_map=color_palette,
        hover_name='streak_name',
        hover_data=['streak_start_game', 'streak_end_game', 'streak_loss']
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title="Consecutive Losing Games",
        yaxis_title="",
        yaxis=dict(
            autorange="reversed",
            showticklabels=False
        )  # Optional: Reverse y-axis to display the first category at the top
    )
    return fig


def form_plot(df: pd.DataFrame):
    fig = px.line(
        df,
        y='all_time_return',
        x='game_overall',
        color='player',
        markers=True,
        template='plotly_white',
        #color_discrete_map=color_palette,
    )

    fig.update_layout(
        height=700,
        #title="Player Return on Investment",  # Chart title
        xaxis_title="Game Number",
        yaxis_title="Return per $$ spent",  # Y-axis label
        yaxis=dict(
            tickprefix='$',  # Adds dollar sign as prefix to y-axis ticks
        ),
        legend=dict(
            title="Player:",
            orientation="h",  # Make the legend horizontal
            yanchor="bottom",  # Anchor the legend at the bottom
            y=-0.2,  # Position it below the plot area
            xanchor="center",  # Center the legend horizontally
            x=0.5  # Center the legend at the middle of the plot
        )
    )

    fig.add_shape(
        type="line",
        x0=df['game_overall'].min(),
        x1=df['game_overall'].max(),
        y0=1,
        y1=1,  # The y-value where the line will be drawn
        line=dict(
            color="Red",
            width=2,
            dash="dashdot",  # Optional: You can make the line dashed or dotted
        )
    )

    fig.add_annotation(
        y=0.9,  # x-position for the text
        x=df['game_overall'].min() + 10,  # y-position for the text (slightly above the line)
        text="Money Line",  # The text to display
        showarrow=False,  # Don't show an arrow pointing to the text
        font=dict(
            size=12,
            color="Red"
        ),
        align="right"
    )

    return fig
