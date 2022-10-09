import sys
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.io as pio
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
from data_getters.get_marvin_data import Marvin_Dashboard_Helpers
from data_getters.get_manual_files import Manual_Dashboard_Helpers

server = flask.Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.DARKLY])


def table_base(week_num: int, year: int):

    week_df = agg_df[(agg_df["year"] == year) & (agg_df["week_number"] == week_num)]
    week_df = week_df[["name", "value", "target", "positive"]]

    sleep_cols = ["Wake", "Bed", "Duration"]

    sleep_df = week_df[week_df["name"].isin(sleep_cols)].drop_duplicates()
    rating_df = week_df[week_df["name"] == "Rating"]

    agg_week_df = (
        week_df[~week_df["name"].isin(sleep_cols + ["Rating"])]
        .groupby(["name", "positive"], as_index=False)
        .agg({"value": "sum", "target": "mean"})
    )

    rating_df = rating_df.groupby(["name", "positive"], as_index=False).agg(
        {"value": "mean", "target": "mean"}
    )

    return pd.concat([agg_week_df, rating_df, sleep_df])[
        ["name", "value", "target", "positive"]
    ]


@app.callback(
    Output("scorecard_table", "data"),
    Output("scorecard_table", "columns"),
    Input("week_dropdown", "value"),
    Input("year_dropdown", "value"),
)
def table_habits(week_num: int, year: int):

    all_data_df = table_base(week_num, year)

    habit_df = all_data_df[~all_data_df["name"].isin(["Wake", "Bed", "Duration"])]

    return habit_df.to_dict("records"), [{"name": i, "id": i} for i in habit_df.columns]


@app.callback(
    Output("supporting_table", "data"),
    Output("supporting_table", "columns"),
    Input("week_dropdown", "value"),
    Input("year_dropdown", "value"),
)
def table_habits(week_num: int, year: int):

    all_data_df = table_base(week_num, year)

    support_df = all_data_df[all_data_df["name"].isin(["Wake", "Bed", "Duration"])]

    support_df = support_df[["name", "value"]]
    support_df["value"] = np.where(
        support_df["name"] != "Duration",
        support_df["value"].apply(lambda x: x.strftime("%I:%M %p")),
        support_df["value"].apply(lambda x: x.strftime("%I:%M")),
    )

    return support_df.to_dict("records"), [
        {"name": i, "id": i} for i in support_df.columns
    ]


app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        html.H1(children="Check-in Dashboard"),
                        style={"width": "100%"},
                    ),
                    width={"size": 7},
                ),
                dbc.Col(
                    html.Div(
                        html.H1(
                            children=datetime.datetime.now().strftime(
                                "%m/%d/%y %a. #%V"
                            )
                        ),
                        style={"width": "100%", "text-align": "right"},
                    ),
                    width={"size": 4},
                ),
            ],
            justify="between",
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
                    html.Div(
                        [
                            dash_table.DataTable(
                                id="scorecard_table",
                                data=[],
                                style_header={
                                    "backgroundColor": "rgb(30, 30, 30)",
                                    "color": "white",
                                },
                                style_data={
                                    "backgroundColor": "rgb(50, 50, 50)",
                                    "color": "white",
                                },
                                style_data_conditional=[
                                    {
                                        "if": {
                                            "filter_query": "({positive} contains 'true' && {value} >= {target}) || ({positive} contains 'false' && {value} <= {target})"
                                        },
                                        "backgroundColor": "#3D9970",
                                        "color": "white",
                                    },
                                    {
                                        "if": {
                                            "filter_query": "({positive} contains 'true' && {value} < {target}) || ({positive} contains 'false' && {value} > {target})"
                                        },
                                        "backgroundColor": "#FF4136",
                                        "color": "white",
                                    },
                                ],
                            )
                        ]
                    ),
                ),
                dbc.Col(
                    html.Div(
                        [
                            dash_table.DataTable(
                                id="supporting_table",
                                data=[],
                                style_header={
                                    "backgroundColor": "rgb(30, 30, 30)",
                                    "color": "white",
                                },
                                style_data={
                                    "backgroundColor": "rgb(50, 50, 50)",
                                    "color": "white",
                                },
                            )
                        ]
                    ),
                ),
            ]
        ),
    ],
    fluid=True,
)

if __name__ == "__main__":

    user_name = "jjm"  # sys.argv[1]
    user_config = get_user_config(user_name)

    day_rating = Exist_Dashboard_Helpers.get_weekly_rating_df(user_config=user_config)
    week_habits_df = Marvin_Dashboard_Helpers.format_habit_df(user_config=user_config)
    sleep_df = Manual_Dashboard_Helpers.format_sleep_df(user_config=user_config)

    agg_df = pd.concat(
        [
            week_habits_df,
            day_rating,
        ]
    )

    sleep_df = sleep_df.merge(
        week_habits_df[["year", "month", "week_number"]].drop_duplicates(),
        on="week_number",
        how="left",
    )

    agg_df = pd.concat([agg_df, sleep_df]).sort_values(["year", "month", "week_number"])

    app.run_server(debug=True)
