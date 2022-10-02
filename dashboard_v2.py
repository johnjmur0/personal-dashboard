import sys
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from datetime import datetime

from dash_files.dashboard_utils import year_dropdown, month_dropdown
from data_getters.utils import get_latest_file, get_user_config
from data_getters.get_finances import Finances_Dashboard_Helpers

server = flask.Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(html.Div(year_dropdown()), width={"size": 3}),
                dbc.Col(html.Div(month_dropdown()), width={"size": 3}),
            ],
            justify="start",
            className="g-0",
        ),
    ],
    fluid=True,
)
