import flask
from datetime import datetime
from dash import Dash, html, dcc, Input, Output, dash_table
import plotly.express as px
import dash_bootstrap_components as dbc
import pandas as pd

from data_getters.utils import get_latest_file
from data_getters.get_marvin_data import Marvin_Processor
from data_getters.get_exist_data import Exist_Processor

server = flask.Flask(__name__)
app = Dash(__name__, server = server, external_stylesheets=[dbc.themes.BOOTSTRAP])

habit_df = Exist_Processor.format_exist_df(get_latest_file(file_prefix = 'exist_data'))
task_df = Marvin_Processor.format_task_df(get_latest_file(file_prefix = 'marvin_tasks'))
finance_df = get_latest_file(file_prefix = 'daily_finances')

@app.callback(
    Output("habit_tracker_scorecard", "data"), 
    Output("habit_tracker_scorecard", "columns"), 
    Input("finance_month_dropdown", "value"), 
    Input("finance_year_dropdown", "value"))
def habit_tracker_scorecard(month, year):

    filtered_df = habit_df[(habit_df['year'] == year) & (habit_df['month'] == month)]

    daily_total_df = filtered_df.groupby(['attribute', 'year', 'month']).agg({'achieved': 'sum'}).astype(int).reset_index(drop = False)
    daily_total_df['day'] = 1
    daily_total_df['datetime'] = pd.to_datetime(daily_total_df[['year', 'month', 'day']])
    daily_total_df['total'] = len(Exist_Processor.key_habits)

    if month == datetime.now().month and year == datetime.now().year:
        daily_total_df['month_days'] = datetime.now().day - 1
    else:    
        daily_total_df['month_days'] = daily_total_df['datetime'].dt.daysinmonth

    display_df = daily_total_df[['attribute', 'achieved', 'month_days']]
    return display_df.to_dict('records'), [{"name": i, "id": i} for i in display_df.columns]

@app.callback(
    Output("monthly_task_piechart", "figure"), 
    Input("finance_month_dropdown", "value"), 
    Input("finance_year_dropdown", "value"))
def task_duration_piechart(month, year):

    filtered_df = task_df[(task_df['year'] == year) & (task_df['month'] == month)] 
    grouped_df = filtered_df.groupby(['category', 'year', 'month']).agg({'duration': 'sum'}).reset_index(drop = False)

    if grouped_df['duration'].sum() == 0:
        grouped_df = pd.DataFrame()

    grouped_df = grouped_df[grouped_df['duration'] > 2]

    fig = px.pie(grouped_df, values = 'duration', names = 'category')

    return fig

def all_profit_loss_barchart():
    
    finance_df['datetime'] = pd.to_datetime(finance_df[['year', 'month', 'day']])
    finance_df['quarter'] = finance_df['datetime'].dt.quarter
    sum_df = finance_df[finance_df['category'] != 'bonus'].groupby(['year', 'quarter']).agg({'total': 'sum'}).reset_index(drop = False)

    quarter_month_map = pd.DataFrame(data = {
        'quarter': [1, 2, 3, 4],
        'month': [1, 4, 7, 10]
    })

    sum_df = sum_df.merge(quarter_month_map, on = 'quarter', how = 'left')
    sum_df['day'] = 1
    sum_df['datetime'] = pd.to_datetime(sum_df[['year', 'month', 'day']])

    fig = px.bar(sum_df, x='datetime', y='total', text_auto='.2s')
    fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    fig.update_xaxes(tickformat='Q%q \n%Y', dtick = 'M3')
    fig.update_layout(yaxis_title=None, xaxis_title = None)

    return fig