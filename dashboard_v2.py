import sys
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import datetime

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
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])


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
        # width=350,
        height=250,
        shapes=[
            go.layout.Shape(
                type="rect",
                xref="paper",
                yref="paper",
                x0=0,
                y0=-0.1,
                x1=1.01,
                y1=1.02,
                line={"width": 1, "color": "black"},
            )
        ],
    )

    return fig


@app.callback(
    Output("scorecard_table", "data"),
    Output("scorecard_table", "columns"),
    Input("week_dropdown", "value"),
    Input("year_dropdown", "value"),
)
def table_demo(week_num: int, year: int):

    week_df = agg_df[(agg_df["year"] == year) & (agg_df["week_number"] == week_num)]
    week_df["tuple"] = list(zip(week_df["count"], week_df["target"]))
    week_df = week_df[["name", "count", "target"]]
    return week_df.to_dict("records"), [{"name": i, "id": i} for i in week_df.columns]


app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        html.H1(children="Check-in Dashboard"),
                        style={"width": "100%"},
                    ),
                    width={"size": 9},
                ),
                dbc.Col(
                    html.Div(
                        html.H1(
                            children=datetime.datetime.now().strftime("%m/%d/%Y %a")
                        ),
                        style={"width": "100%"},
                    ),
                    width={"size": 3},
                ),
            ],
            justify="start",
            className="g-0",
        ),
        dbc.Row(
            [
                dbc.Col(html.Div(year_dropdown()), width={"size": 4}),
                dbc.Col(html.Div(month_dropdown()), width={"size": 4}),
                dbc.Col(html.Div(week_dropdown()), width={"size": 4}),
            ],
            justify="start",
            className="g-0",
        ),
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.Label("Aggregation: "),
                            aggregation_radio(),
                        ],
                        style={
                            "width": "100%",
                            "font-size": 20,
                            "display": "flex",
                        },
                    ),
                    width="auto",
                ),
            ],
            justify="center",
            className="g-0",
        ),
        dbc.Row(
            [
                dbc.Col(
                    html.Div([dash_table.DataTable(id="scorecard_table", data=[])]),
                ),
            ]
        ),
    ],
    fluid=True,
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

    marvin_habits_df["year"] = pd.to_datetime(marvin_habits_df["timestamp"]).dt.year
    marvin_habits_df["month"] = pd.to_datetime(marvin_habits_df["timestamp"]).dt.month

    week_habits_df = marvin_habits_df.groupby(
        ["name", "positive", "period", "week_number", "year", "month"], as_index=False
    ).agg({"count": "sum", "target": "mean"})

    day_rating["week_number"] = day_rating["date"].dt.isocalendar().week
    day_rating["name"] = "rating"

    day_rating = day_rating.groupby(
        ["year", "month", "week_number"], as_index=False
    ).agg({"value": "mean", "target": "mean"})

    agg_df = pd.concat(
        [
            week_habits_df[["name", "week_number", "year", "month", "count", "target"]],
            day_rating.rename(columns={"value": "count"}),
        ]
    )

    sleep_df = (
        manual_sleep_df.melt(
            id_vars="week", value_vars=["wakeup", "bedtime", "duration"]
        )
        .rename(columns={"week": "week_number", "variable": "name", "value": "count"})
        .merge(
            week_habits_df[["year", "month", "week_number"]].drop_duplicates(),
            on="week_number",
            how="left",
        )
    )
    sleep_df = sleep_df[~pd.isnull(sleep_df["year"])]
    sleep_df["target"] = np.where(
        sleep_df["name"] == "bedtime", datetime.time(22, 0, 0), datetime.time(6, 0, 0)
    )

    agg_df = pd.concat([agg_df, sleep_df]).sort_values(["year", "month", "week_number"])

    app.run_server(debug=True)
