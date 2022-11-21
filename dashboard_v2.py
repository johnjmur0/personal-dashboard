import sys
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
from dash_bootstrap_templates import load_figure_template
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
from data_getters.utils import Data_Getter_Utils
from data_getters.get_finances import Finances_Dashboard_Helpers
from data_getters.get_exist_data import Exist_Dashboard_Helpers
from data_getters.get_marvin_data import Marvin_Dashboard_Helpers
from data_getters.get_manual_files import Manual_Dashboard_Helpers

load_figure_template("darkly")
server = flask.Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.DARKLY])


@app.callback(
    Output("monthly_finance_barchart", "figure"),
    Input("month_dropdown", "value"),
    Input("year_dropdown", "value"),
)
def monthly_finance_barchart(month: int, year: int):

    filter_df = Finances_Dashboard_Helpers.create_spend_budget_df(
        finance_df, budget_df, year, month
    )

    fig = px.bar(
        filter_df,
        x="category",
        y="value",
        color="variable",
        barmode="group",
        text_auto=".2s",
        color_discrete_sequence=["blue", "grey"],
        template="darkly",
    )

    fig.update_traces(
        textfont_size=12, textangle=0, textposition="outside", cliponaxis=False
    )
    fig.update_layout(margin=dict(r=0, l=0), yaxis_title=None, xaxis_title=None)

    return fig


@app.callback(
    Output("accounts_table", "data"),
    Output("accounts_table", "columns"),
    Input("profit_target", "value"),
    Input("saving_months", "value"),
)
def accounts_table(
    profit_target: int,
    saving_months: int,
    historical_start_year: int = 2022,
):

    pivot_account_df = pd.pivot_table(
        account_df[["account_type", "total"]], values="total", columns=["account_type"]
    )

    avg_spend_df = (
        finance_df[finance_df["year"] >= historical_start_year]
        .groupby(["year", "month", "category"])
        .agg({"total": "sum"})
        .groupby(["category"])
        .agg({"total": "mean"})
        .reset_index(drop=False)
    )

    avg_spend_df = avg_spend_df[~avg_spend_df["category"].isin(["loans", "bonus"])]

    monthly_df = (
        avg_spend_df[
            avg_spend_df["category"].isin(["income", "investments", "housing"])
        ]
        .pivot_table(values="total", columns="category")
        .reset_index(drop=True)
    )

    monthly_df["spending"] = avg_spend_df.loc[
        avg_spend_df["category"].isin(["discretionary", "groceries"]), ["total"]
    ].sum()[0]

    monthly_df["savings"] = (
        monthly_df["income"]
        + monthly_df["spending"]
        + monthly_df["investments"]
        + monthly_df["housing"]
    )

    final_df = pd.concat(
        [pivot_account_df.reset_index(drop=True), monthly_df.reset_index(drop=True)],
        axis=1,
    )

    final_df["cash savings"] = (
        (final_df["housing"] + final_df["spending"] + final_df["investments"])
        * saving_months
        * -1
    )
    final_df["excess savings"] = final_df["bank"] - final_df["cash savings"]

    final_cols = [
        "bank",
        "investment",
        "cash savings",
        "excess savings",
        "income",
        "spending",
        "housing",
        "savings",
        "investments",
    ]
    final_df = pd.melt(final_df, id_vars=[], value_vars=final_cols)

    final_df["total"] = round(final_df["value"], -1)
    final_df.drop(columns=["value"], inplace=True)
    final_df = final_df.apply(
        lambda x: [f"${y:,.0f}" for y in x] if x.name == "total" else x
    )

    return final_df.to_dict("records"), [{"name": i, "id": i} for i in final_df.columns]


def table_base(week_num: int, month: int, year: int, agg_str: str):

    if agg_str == "week":
        select_df = agg_df[
            (agg_df["year"] == year) & (agg_df["week_number"] == week_num)
        ]
    elif agg_str == "month":
        select_df = agg_df[(agg_df["year"] == year) & (agg_df["month"] == month)]

    select_df = select_df[["name", "value", "target", "positive", "week_number"]]

    sleep_cols = ["Wake", "Bed", "Duration"]

    sleep_df = select_df[select_df["name"].isin(sleep_cols)].drop_duplicates()
    rating_df = select_df[select_df["name"] == "Rating"]

    select_df["week_count"] = len(select_df["week_number"].unique())

    agg_week_df = (
        select_df[~select_df["name"].isin(sleep_cols + ["Rating"])]
        .groupby(["name", "positive"], as_index=False)
        .agg({"value": "sum", "target": "mean", "week_count": "max"})
    )

    agg_week_df["target"] = agg_week_df["target"] * agg_week_df["week_count"]

    rating_df = rating_df.groupby(["name", "positive"], as_index=False).agg(
        {"value": "mean", "target": "mean"}
    )
    rating_df["value"] = round(rating_df["value"], 2)

    return pd.concat([agg_week_df, rating_df, sleep_df])[
        ["name", "value", "target", "positive"]
    ]


@app.callback(
    Output("scorecard_table", "data"),
    Output("scorecard_table", "columns"),
    Input("week_dropdown", "value"),
    Input("month_dropdown", "value"),
    Input("year_dropdown", "value"),
    Input("aggregation_radio", "value"),
)
def scorecard_table(week_num: int, month: int, year: int, agg_str: str):

    all_data_df = table_base(week_num, month, year, agg_str)

    habit_df = all_data_df[~all_data_df["name"].isin(["Wake", "Bed", "Duration"])]

    return habit_df.to_dict("records"), [{"name": i, "id": i} for i in habit_df.columns]


@app.callback(
    Output("supporting_table", "data"),
    Output("supporting_table", "columns"),
    Input("week_dropdown", "value"),
    Input("month_dropdown", "value"),
    Input("year_dropdown", "value"),
    Input("aggregation_radio", "value"),
)
def supporting_table(week_num: int, month: int, year: int, agg_str: str):

    all_data_df = table_base(week_num, month, year, agg_str)

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
        # Header
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
        # Dropdowns
        dbc.Row(
            [
                dbc.Col(html.Div(year_dropdown()), width={"size": 4}),
                dbc.Col(html.Div(month_dropdown()), width={"size": 4}),
                dbc.Col(html.Div(week_dropdown()), width={"size": 4}),
            ],
            justify="start",
            className="g-0",
        ),
        # Aggregation Radio
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
        # Tables
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
        # Finance inputs
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            "Savings (Months): ",
                            dcc.Input(id="saving_months", value=8, type="number"),
                        ]
                    ),
                    style={"textAlign": "right"},
                    width={"size": 2},
                ),
                dbc.Col(
                    html.Div(
                        [
                            "Profit Target: ",
                            dcc.Input(
                                id="profit_target", value=3000, type="number", step=100
                            ),
                        ]
                    ),
                    style={"textAlign": "right"},
                    width={"size": 2},
                ),
            ],
            justify="end",
        ),
        # Graph + finance table
        dbc.Row(
            [
                dbc.Col(
                    html.Div([dcc.Graph(id="monthly_finance_barchart")]),
                    width={"size": 6},
                ),
                dbc.Col(
                    html.Div(
                        [
                            dash_table.DataTable(
                                id="accounts_table",
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
                    width={"size": 2},
                ),
            ],
            justify="around",
            align="center",
        ),
    ],
    fluid=True,
)

if __name__ == "__main__":

    user_name = sys.argv[1]
    user_config = Data_Getter_Utils.get_user_config(user_name)

    day_rating = Exist_Dashboard_Helpers.get_weekly_rating_df(user_config=user_config)
    week_habits_df = Marvin_Dashboard_Helpers.format_habit_df(user_config=user_config)
    sleep_df = Manual_Dashboard_Helpers.format_sleep_df(user_config=user_config)

    agg_df = pd.concat([week_habits_df, day_rating])

    sleep_df = sleep_df.merge(
        week_habits_df[["year", "month", "week_number"]].drop_duplicates(),
        on="week_number",
        how="left",
    )

    agg_df = pd.concat([agg_df, sleep_df]).sort_values(["year", "month", "week_number"])

    budget_df = Finances_Dashboard_Helpers.get_general_budget(user_config)
    finance_df = Data_Getter_Utils.get_latest_file(file_prefix="daily_finances")
    month_sum_df = Finances_Dashboard_Helpers.get_month_sum_df(finance_df)
    account_df = Data_Getter_Utils.get_latest_file(file_prefix="account_totals")

    app.run_server(debug=True)
