import sys
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from dash_files.dashboard_utils import (
    year_dropdown,
    month_dropdown,
    week_dropdown,
    aggregation_radio,
)
from data_getters.utils import get_latest_file, get_user_config
from data_getters.get_finances import Finances_Dashboard_Helpers
from data_getters.get_exist_data import Exist_Dashboard_Helpers
from data_getters.get_manual_files import Manual_Processor

server = flask.Flask(__name__)
app = Dash(__name__, server=server)


def make_indicator_ex():

    fig = go.Figure()

    fig.add_trace(
        go.Indicator(
            value=200,
            delta={"reference": 160},
            gauge={"axis": {"visible": False}},
            domain={"row": 0, "column": 0},
        )
    )

    fig.add_trace(
        go.Indicator(
            value=120,
            gauge={"shape": "bullet", "axis": {"visible": True}},
            domain={"x": [0.05, 0.5], "y": [0.15, 0.35]},
        )
    )

    fig.add_trace(
        go.Indicator(mode="number+delta", value=300, domain={"row": 0, "column": 1})
    )

    fig.add_trace(go.Indicator(mode="delta", value=40, domain={"row": 1, "column": 1}))

    fig.update_layout(
        grid={"rows": 2, "columns": 2, "pattern": "independent"},
        template={
            "data": {
                "indicator": [
                    {
                        "title": {"text": "Speed"},
                        "mode": "number+delta+gauge",
                        "delta": {"reference": 90},
                    }
                ]
            }
        },
    )

    return fig


def simple_indicator(value: int, target: int, title: str):

    fig = go.Figure()

    fig.add_trace(
        go.Indicator(mode="number+delta", value=value, domain={"row": 0, "column": 1})
    )

    fig.update_layout(
        template={
            "data": {
                "indicator": [
                    {
                        "title": {"text": title},
                        "mode": "number+delta+gauge",
                        "delta": {"reference": target},
                    }
                ]
            }
        },
    )

    return fig


app.layout = html.Div(
    children=[
        html.H1(
            children="Check-in Dashboard",
        ),
        aggregation_radio(),
        year_dropdown(),
        month_dropdown(),
        week_dropdown(),
        html.Div(
            children=[
                dcc.Graph(figure=simple_indicator(6, 6, "exercise")),
                dcc.Graph(figure=simple_indicator(4, 6, "reading")),
                dcc.Graph(figure=simple_indicator(1, 6, "sleep")),
            ],
            style={"width": "25%", "height": "25%"},
        ),
    ],
)

if __name__ == "__main__":

    user_name = "jjm"  # sys.argv[1]
    user_config = get_user_config(user_name)

    exist_df = Exist_Dashboard_Helpers.format_exist_df(
        get_latest_file(file_prefix="exist_data"), get_user_config("jjm")
    )

    day_rating = exist_df[exist_df["attribute"] == "mood"]
    marvin_habits_df = get_latest_file(file_prefix="marvin_habits")
    manual_sleep_df = Manual_Processor.get_sleep_df(user_name)

    week_habits_df = marvin_habits_df.groupby(
        ["name", "positive", "period", "week_number"], as_index=False
    ).agg({"count": "sum", "target": "mean"})

    day_rating["week_number"] = day_rating["date"].dt.isocalendar().week

    app.run_server(debug=True)
