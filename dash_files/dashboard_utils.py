import sys
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from datetime import datetime

def year_dropdown():

    return dcc.Dropdown(
        id="finance_year_dropdown",
        options=list(range(datetime.now().year - 4, datetime.now().year + 1)),
        value=datetime.now().year,
        clearable=False,
    )


def month_dropdown():
    return dcc.Dropdown(
        id="finance_month_dropdown",
        options=list(range(1, 13)),
        value=datetime.now().month,
        clearable=False,
    )