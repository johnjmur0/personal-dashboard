import sys
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from datetime import datetime
from typing import List, Set


valid_agg_vals = set(["week", "month", "quarter", "year"])


def year_dropdown():
    return dcc.Dropdown(
        id="year_dropdown",
        options=list(range(datetime.now().year - 4, datetime.now().year + 1)),
        value=datetime.now().year,
        clearable=False,
    )


def month_dropdown():
    return dcc.Dropdown(
        id="month_dropdown",
        options=list(range(1, 13)),
        value=datetime.now().month,
        clearable=False,
    )


def week_dropdown():
    return dcc.Dropdown(
        id="week_dropdown",
        options=list(range(1, 53)),
        value=datetime.now().isocalendar().week - 1,
        clearable=False,
    )


def variable_dropdown(var_list: List[str]):
    return dcc.Dropdown(
        id="variable_dropdown",
        options=var_list,
        value="spending",
        clearable=False,
    )


def aggregation_radio():
    return dcc.RadioItems(
        id="aggregation_radio",
        options=list(valid_agg_vals),
        value="week",
        inline=True,
        inputStyle={
            "margin-right": "3px",
            "margin-left": "7px",
            "margin-top": "3px",
        },
    )


def filter_monthly_df(
    df: pd.DataFrame, month: int, year: int, week_num: int, agg_str: str
) -> pd.DataFrame:
    if agg_str == "week":
        select_df = df[(df["year"] == year) & (df["week_number"] == week_num)]
    elif agg_str == "month":
        select_df = df[(df["year"] == year) & (df["month"] == month)]
    elif agg_str == "year":
        select_df = df[(df["year"] == year)]
    elif agg_str == "quarter":
        select_quarter = list(df[(df["month"] == month)]["quarter"])[0]
        select_df = df[(df["year"] == year) & (df["quarter"] == select_quarter)]

    return select_df


def get_agg_vec(agg_str: str) -> List[str]:
    if agg_str == "week":
        ret_vec = valid_agg_vals
    elif agg_str == "month":
        ret_vec = valid_agg_vals - set(["week"])
    elif agg_str == "quarter":
        ret_vec = valid_agg_vals - set(["week", "month"])
    elif agg_str == "year":
        ret_vec = valid_agg_vals - set(["week", "month", "quarter"])
    else:
        raise ValueError(
            f"Unexpected agg_str {agg_str} passed. Only ','.join({valid_agg_vals}) allowed"
        )

    return list(ret_vec)


def add_quarter_col(df: pd.DataFrame):
    df["date"] = pd.to_datetime(df[["year", "month"]].assign(day=1))
    df["quarter"] = df["date"].dt.quarter

    return df
