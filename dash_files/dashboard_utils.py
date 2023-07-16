import sys
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from datetime import datetime


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


def aggregation_radio():
    return dcc.RadioItems(
        id="aggregation_radio",
        options=["week", "month", "quarter", "year"],
        value="week",
        inline=True,
        inputStyle={
            "margin-right": "3px",
            "margin-left": "7px",
            "margin-top": "3px",
        },
    )


def aggregate_monthly_df(
    df: pd.DataFrame, month: int, year: int, week_num: int, agg_str: str
) -> pd.DataFrame:
    if agg_str == "week":
        select_df = df[(df["year"] == year) & (df["week_number"] == week_num)]
    elif agg_str == "month":
        select_df = df[(df["year"] == year) & (df["month"] == month)]
    elif agg_str == "year":
        select_df = df[(df["year"] == year)]
    elif agg_str == "quarter":
        df["date"] = pd.to_datetime(df[["year", "month"]].assign(day=1))
        df["quarter"] = df["date"].dt.quarter
        select_quarter = list(df[(df["month"] == month)]["quarter"])[0]
        select_df = df[(df["year"] == year) & (df["quarter"] == select_quarter)]

    return select_df
