import sys
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from datetime import datetime
from typing import List, Set


valid_agg_vals = set(["week", "month", "quarter", "year"])
quarter_dict = {
    1: 1,
    2: 1,
    3: 1,
    4: 2,
    5: 2,
    6: 2,
    7: 3,
    8: 3,
    9: 3,
    10: 4,
    11: 4,
    12: 4,
}

timeseries_vars = ["spend", "income", "profit", "category_spend"]


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


def variable_dropdown(extra_var_list: List[str] = []):
    return dcc.Dropdown(
        id="variable_dropdown",
        options=timeseries_vars + extra_var_list,
        value="spend",
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
        select_quarter = quarter_dict[month]
        select_df = df[(df["year"] == year) & (df["quarter"] == select_quarter)]
    else:
        raise ValueError(
            f"Unexpected agg_str {agg_str} passed. Only ','.join({valid_agg_vals}) allowed"
        )

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


def forge_datetime_col(agg_str: str, df: pd.DataFrame) -> pd.DataFrame:
    if agg_str == "week":
        df["datetime"] = pd.to_datetime(
            df[["year", "month", "week"]].astype(str).agg("-".join, axis=1) + "-1",
            format="%Y-%m-%W",
        )
    elif agg_str == "month":
        df["datetime"] = pd.to_datetime(
            df[["year", "month"]].astype(str).agg("-".join, axis=1) + "-1",
            format="%Y-%m",
        )
    elif agg_str == "quarter":
        df["month"] = (df["quarter"] - 1) * 3 + 1
        df["datetime"] = pd.to_datetime(
            df[["year", "month"]].astype(str).agg("-".join, axis=1) + "-1",
            format="%Y-%m",
        )
    elif agg_str == "year":
        df["datetime"] = pd.to_datetime(df["year"].astype(str), format="%Y")
    else:
        raise ValueError(
            f"Unexpected agg_str {agg_str} passed. Only ','.join({valid_agg_vals}) allowed"
        )

    return df.sort_values("datetime")
