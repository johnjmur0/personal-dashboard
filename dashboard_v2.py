import sys
import time
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
from dash_bootstrap_templates import load_figure_template
import dash_bootstrap_components as dbc

import plotly.io as pio
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pandas.api.types import CategoricalDtype
import numpy as np
import datetime

from dash_files.dashboard_utils import (
    year_dropdown,
    month_dropdown,
    week_dropdown,
    aggregation_radio,
    aggregate_monthly_df,
)
from data_getters.utils import Data_Getter_Utils
from data_getters.get_mint_data import Finances_Dashboard_Helpers
from data_getters.get_exist_data import Exist_Dashboard_Helpers
from data_getters.get_marvin_data import Marvin_Dashboard_Helpers
from data_getters.get_manual_files import Manual_Dashboard_Helpers

template_name = "superhero"
load_figure_template(template_name)
server = flask.Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.SUPERHERO])


@app.callback(
    Output("monthly_finance_barchart", "figure"),
    Input("month_dropdown", "value"),
    Input("year_dropdown", "value"),
    Input("aggregation_radio", "value"),
)
def monthly_finance_barchart(month: int, year: int, agg_str: str):
    filter_df = Finances_Dashboard_Helpers.create_spend_budget_df(
        finance_df, budget_df, year, month, agg_str
    )

    filter_df["diff"] = (filter_df["total"] - filter_df["budget"]) * -1
    filter_df["diff"] = np.where(abs(filter_df["diff"]) == np.Inf, 0, filter_df["diff"])

    filter_df["positive"] = np.where(
        filter_df["diff"] < 0, "Under-Budget", "Over-Budget"
    )
    color_map = {"Under-Budget": "#5cb85c", "Over-Budget": "#d9534f"}

    fig = px.bar(
        filter_df,
        x="diff",
        y="category",
        color="positive",
        barmode="group",
        text_auto=".2s",
        template=template_name,
        color_discrete_map=color_map,
    )

    fig.add_vline(x=0, line_dash="dash", line_color="red")

    fig.update_traces(
        textfont_size=12, textangle=0, textposition="outside", cliponaxis=False
    )
    fig.update_layout(
        margin=dict(r=0, l=0),
        yaxis_title=None,
        xaxis_title=None,
        yaxis=dict(tickfont=dict(size=16)),
        title={
            "text": "Budget Evaluation",
            "xanchor": "center",
            "yanchor": "top",
            "y": 0.95,
            "x": 0.5,
        },
    )

    return fig


@app.callback(
    Output("accounts_table", "children"),
    Input("profit_target", "value"),
    Input("saving_months", "value"),
    Input("month_dropdown", "value"),
    Input("year_dropdown", "value"),
    Input("aggregation_radio", "value"),
)
def accounts_table(
    profit_target: int,
    saving_months: int,
    month: int,
    year: int,
    agg_str: str,
    historical_start_year: int = 2022,
):
    pivot_account_df = pd.pivot_table(
        account_df[["account_type", "total"]], values="total", columns=["account_type"]
    )

    if agg_str == "week":
        agg_str = "month"

    select_df = aggregate_monthly_df(finance_df, month, year, 0, agg_str)

    distinct_categories = ["paycheck", "investments", "bonus"]

    spend = select_df[~select_df["category"].isin(distinct_categories)]["total"].sum()
    income = select_df[select_df["category"].isin(["paycheck", "bonus"])]["total"].sum()
    profit = income + spend
    budget = budget_df["budget"].sum()

    ret_df = pd.DataFrame(
        data={
            "budget": budget,
            "spending": spend,
            "delta": budget - abs(spend),
            "paycheck": income,
            "savings": profit,
        },
        index=[0],
    )

    final_df = pd.concat(
        [pivot_account_df.reset_index(drop=True), ret_df.reset_index(drop=True)],
        axis=1,
    )

    final_cols = [
        "bank",
        "investment",
        "paycheck",
        "spending",
        "budget",
        "delta",
        "savings",
    ]
    final_df = pd.melt(final_df, id_vars=[], value_vars=final_cols)

    col_name = f"total"
    final_df[col_name] = round(final_df["value"], -1)
    final_df.drop(columns=["value"], inplace=True)
    final_df = final_df.apply(
        lambda x: [f"${y:,.0f}" for y in x] if x.name == col_name else x
    )

    return dbc.Table.from_dataframe(final_df, striped=True, bordered=True, hover=True)


def table_base(week_num: int, month: int, year: int, agg_str: str):
    sleep_vals = ["Wake", "Bed", "Duration"]

    select_df = aggregate_monthly_df(agg_df, month, year, week_num, agg_str)

    select_df = select_df[["name", "value", "target", "positive", "week_number"]]
    select_df["week_count"] = len(select_df["week_number"].unique())

    agg_week_df = (
        select_df[~select_df["name"].isin(sleep_vals + ["Rating"])]
        .groupby(["name", "positive"], as_index=False)
        .agg({"value": "sum", "target": "mean", "week_count": "max"})
    )
    agg_week_df["target"] = agg_week_df["target"] * agg_week_df["week_count"]

    rating_df = select_df[select_df["name"] == "Rating"]
    rating_df = rating_df.groupby(["name", "positive"], as_index=False).agg(
        {"value": "mean", "target": "mean"}
    )
    rating_df["value"] = round(rating_df["value"], 2)

    sleep_df = select_df[select_df["name"].isin(sleep_vals)]
    ret_sleep_df = Manual_Dashboard_Helpers.get_avg_sleep_df(sleep_df)

    return pd.concat([agg_week_df, rating_df, ret_sleep_df])[
        ["name", "value", "target", "positive"]
    ]


@app.callback(
    Output("scorecard_table_positive", "children"),
    Output("scorecard_table_negative", "children"),
    Input("week_dropdown", "value"),
    Input("month_dropdown", "value"),
    Input("year_dropdown", "value"),
    Input("aggregation_radio", "value"),
)
def scorecard_table(week_num: int, month: int, year: int, agg_str: str):
    all_data_df = table_base(week_num, month, year, agg_str)

    habit_df = all_data_df[~all_data_df["name"].isin(["Wake", "Bed", "Duration"])]

    success_df = habit_df[
        ((habit_df["positive"]) & (habit_df["value"] >= habit_df["target"]))
        | ((~habit_df["positive"]) & (habit_df["value"] <= habit_df["target"]))
    ]
    fail_df = habit_df[
        ((habit_df["positive"]) & (habit_df["value"] < habit_df["target"]))
        | ((~habit_df["positive"]) & (habit_df["value"] > habit_df["target"]))
    ]
    return dbc.Table.from_dataframe(
        success_df.drop(columns={"positive"}),
        striped=True,
        bordered=True,
        hover=True,
        color="success",
    ), dbc.Table.from_dataframe(
        fail_df.drop(columns={"positive"}),
        striped=True,
        bordered=True,
        hover=True,
        color="danger",
    )


@app.callback(
    Output("supporting_table", "children"),
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
        support_df["value"].apply(lambda x: pd.to_datetime(x).strftime("%I:%M %p")),
        support_df["value"].apply(lambda x: pd.to_datetime(x).strftime("%I:%M")),
    )

    cat_support_data = CategoricalDtype(["Wake", "Bed", "Duration"], ordered=True)
    support_df["name"] = support_df["name"].astype(cat_support_data)
    support_df = support_df.sort_values("name")

    return dbc.Table.from_dataframe(support_df, striped=True, bordered=True, hover=True)


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
                            "height": 30,
                            "display": "flex",
                            "float": "left",
                            "margin-bottom": 3,
                            "margin-top": 10,
                        },
                    ),
                    width="auto",
                ),
            ],
            justify="center",
            className="g-0",
        ),
        # Scorecard Tables
        dbc.Row(
            [
                dbc.Col(
                    html.Div(id="scorecard_table_positive"),
                ),
                dbc.Col(
                    html.Div(id="scorecard_table_negative"),
                    width={"size": 6},
                ),
            ],
            justify="between",
        ),
        # Supporting table and finance inputs
        dbc.Row(
            [
                dbc.Col(
                    html.Div(id="supporting_table"),
                    width={"size": 6},
                ),
                dbc.Col(
                    html.Div(
                        [
                            "Savings (Months): ",
                            dcc.Input(id="saving_months", value=8, type="number"),
                        ]
                    ),
                    style={"textAlign": "right"},
                    width={"size": 2},
                    align="center",
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
                    align="center",
                ),
            ],
            justify="between",
        ),
        # Graph + accounts table
        dbc.Row(
            [
                dbc.Col(
                    html.Div([dcc.Graph(id="monthly_finance_barchart")]),
                    width={"size": 7},
                ),
                dbc.Col(
                    html.Div(id="accounts_table"),
                    width={"size": 3},
                    align="center",
                ),
            ],
            justify="around",
        ),
    ],
    fluid=True,
    className="dbc",
)

if __name__ == "__main__":
    user_name = "jjm"
    data_getter = Data_Getter_Utils()
    user_config = data_getter.get_user_config(user_name)

    exist_data = data_getter.get_latest_file(file_prefix="exist_data")
    day_rating = Exist_Dashboard_Helpers.get_weekly_rating_df(
        exist_data, user_config=user_config
    )

    marvin_data = data_getter.get_latest_file(file_prefix="marvin_habits")
    week_habits_df = Marvin_Dashboard_Helpers.format_habit_df(
        marvin_data, user_config=user_config
    )

    sleep_df = data_getter.get_latest_file(file_prefix="sleep_data")
    sleep_df = Manual_Dashboard_Helpers.format_sleep_df(
        sleep_df=sleep_df, user_config=user_config
    )

    agg_df = pd.concat([week_habits_df, day_rating, sleep_df]).sort_values(
        ["year", "month", "week_number"]
    )

    budget_df = data_getter.get_latest_file(file_prefix="monthly_budget")
    finance_df = data_getter.get_latest_file(file_prefix="daily_finances")
    account_df = data_getter.get_latest_file(file_prefix="account_totals")

    month_sum_df = Finances_Dashboard_Helpers.get_month_sum_df(finance_df)

    app.run_server(debug=True)
