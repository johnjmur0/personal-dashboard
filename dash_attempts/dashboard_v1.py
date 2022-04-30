from operator import index
import os
import glob
from sys import prefix
from tokenize import group
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime

server = flask.Flask(__name__)
app = Dash(__name__, server = server, external_stylesheets=[dbc.themes.BOOTSTRAP])

def format_task_df(task_df):
    
    task_df = task_df[task_df['day'] != 'unassigned']
    task_df['day'] = pd.to_datetime(task_df['day'])
    task_df['month'] = task_df['day'].dt.month
    task_df['year'] = task_df['day'].dt.year

    task_df[['sub_project_2', 'sub_project', 'main_category', 'main_category_dupe']] = task_df['parent'].str.split('/', expand = True)

    aggregate_categories = ['Orsted', 'Edison Energy', 'Music']
    task_df['end_val'] = np.where(
        task_df['category'].isin(aggregate_categories), 
        task_df['category'], 
        task_df['sub_project_2'])

    task_df.drop(columns = {'main_category_dupe', 'category', 'sub_project', 'sub_project_2', 'parent'}, inplace=True)
    task_df.rename(columns = {'end_val': 'category'}, inplace=True)

    return task_df

def format_exist_df(exist_df, key_habits):

    habit_df = exist_df[exist_df['attribute'].isin(key_habits['attribute'])]
    habit_df = habit_df.astype({'value': 'float64'})
    habit_df = habit_df.merge(key_habits, on='attribute', how='left')

    habit_df['value'] = np.where(habit_df['attribute'] == 'sleep_start', ((habit_df['value'] / 60) + 12) % 24, habit_df['value'])
    habit_df['value'] = np.where(habit_df['attribute'] == 'sleep_end', habit_df['value'] / 60, habit_df['value'])

    habit_df['achieved'] = np.where(
        habit_df['attribute'].isin(['sleep_start', 'sleep_end']), 
        habit_df['value'] <= habit_df['success'], 
        habit_df['value'] >= habit_df['success'])

    habit_df['date'] = pd.to_datetime(habit_df['date'])
    habit_df['year'] = habit_df['date'].dt.year
    habit_df['month'] = habit_df['date'].dt.month  

    return habit_df

def get_latest_file(file_prefix):
    cache_dir = './temp_cache'
    files = glob.glob(f'{cache_dir}/{file_prefix}*')

    latest_date = pd.to_datetime('1/1/2019')
    for file in files:
        file_name = os.path.basename(file)
        split_filename = file_name.split('_')

        if len(split_filename) < 3:
            continue

        date = pd.to_datetime(split_filename[2].replace('.csv', ''))
        if date > latest_date:
            latest_date = date.date()
        
    file_path = [x for x in files if latest_date.strftime('%Y-%m-%d') in x]

    if len(file_path) == 0:
        raise ValueError(f'No dated file for prefix {file_prefix}!')
    
    ret_df = pd.read_csv(file_path[0], index_col = None)
    return ret_df
    
def get_month_sum_df(finance_df):

    month_sum_df = finance_df[~finance_df['category'] \
    .isin(['bonus', 'investment'])].groupby(['year', 'month']) \
    .agg({'total': 'sum'}).reset_index(drop = False)
    
    return month_sum_df

finance_df = get_latest_file(file_prefix = 'daily_finances')
task_df = get_latest_file(file_prefix = 'marvin_tasks')
exist_df = get_latest_file(file_prefix = 'exist_data')

key_habits = pd.DataFrame( data = {
        'attribute': ['exercise', 'sleep_start', 'sleep_end', 'steps', 'free_in_am', 'got_outside', 'read', 'mood'],
        'success': [1, 10.5, 7.5, 4000, 1, 1, 1, 6]
    })

task_df = format_task_df(task_df)
habit_df = format_exist_df(exist_df, key_habits)

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

@app.callback(
    Output("monthly_free_cash_lineplot", "figure"),
    Input("profit_target", "value"))
def free_cashflow_line_plot(monthly_saving_target):

    month_sum_df = get_month_sum_df(finance_df)
    month_sum_df['free_cash'] = month_sum_df['total'] - monthly_saving_target
    month_sum_df['free_cash'] = month_sum_df['free_cash'].cumsum()
    month_sum_df['day'] = 1
    month_sum_df['datetime'] = pd.to_datetime(month_sum_df[['year', 'month', 'day']])

    fig = px.line(month_sum_df, x = 'datetime', y= 'free_cash')

    return fig

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
    daily_total_df['total'] = len(key_habits)

    if month == datetime.now().month and year == datetime.now().year:
        daily_total_df['month_days'] = datetime.now().day - 1
    else:    
        daily_total_df['month_days'] = daily_total_df['datetime'].dt.daysinmonth

    display_df = daily_total_df[['attribute', 'achieved', 'month_days']]
    return display_df.to_dict('records'), [{"name": i, "id": i} for i in display_df.columns]

@app.callback(
    Output("monthly_finance_barchart", "figure"), 
    Input("finance_month_dropdown", "value"), 
    Input("finance_year_dropdown", "value"),
    Input("profit_target", "value"),
    Input("housing_payment", "value"))
def monthly_finance_barchart(month, year, profit_target, housing_payment):
    
    filter_df = finance_df[(finance_df['year'] == year) & (finance_df['month'] == month)].groupby('category').agg({'total': 'sum'}).reset_index(drop = False)
    
    general_budget = pd.DataFrame(data = {
        'category': ['housing', 'groceries', 'discretionary'],
        'budget': [housing_payment * -1.05, -400, (profit_target + (housing_payment * -1.05 - 400)) * -1]
    })

    filter_df = filter_df.merge(general_budget, how = 'left', on = 'category')

    sum_df = pd.DataFrame(data = {
        'year': [year],
        'month': [month],
        'category': 'profit/loss',
        'budget': [profit_target],
        'total': [filter_df['total'].sum()]
    })

    filter_df = pd.concat([filter_df, sum_df])
    
    filter_df = filter_df[abs(filter_df['total']) > 100]

    filter_df = pd.melt(filter_df, id_vars = ['category', 'year', 'month'], value_vars = ['total', 'budget'])

    fig = px.bar(filter_df, x='category', y='value', color='variable', barmode = 'group', text_auto = '.2s', 
                    color_discrete_sequence = ['blue', 'grey'])

    fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    fig.update_layout(yaxis_title=None, xaxis_title = None)

    return fig

@app.callback(
    Output("avg_category_piechart", "figure"), 
    Input("profit_target", "value"),
    Input("housing_payment", "value"),
    Input("historical_start_year", "value"))
def avg_category_piechart(profit_target, housing_payment, historical_start_year):
    
    month_sum_df = get_month_sum_df(finance_df)

    month_sum_df = month_sum_df[month_sum_df['year'] >= historical_start_year]
    month_sum_df['free_cash'] = month_sum_df['total'] - profit_target

    month_sum_df = pd.melt(month_sum_df, id_vars = ['year', 'month'], value_vars = ['total', 'free_cash'])
    month_sum_df.rename(columns = {'variable': 'category', 'value': 'total'}, inplace = True)
    month_sum_df.loc[month_sum_df['category'] == 'total', ['category']] = 'saving'

    historical_df = finance_df[
        (finance_df['year'] >= historical_start_year) & 
        ~((finance_df['year'] == datetime.now().year) & (finance_df['month'] == datetime.now().month))]

    avg_df = pd.concat(
        [
            historical_df.groupby(['year', 'month', 'category']).agg({'total': 'sum'}).reset_index(drop = False),
            month_sum_df
        ]).groupby(['category']).agg({'total': 'mean'}).reset_index(drop = False)

    avg_df = avg_df[~avg_df['category'].isin(['bonus', 'loans', 'music', 'free_cash'])]
    avg_df.loc[avg_df['category'] == 'housing', ['total']] = housing_payment
    avg_df['income'] = list(avg_df[avg_df['category'] == 'income']['total'])[0]

    avg_df['percentage'] = abs(avg_df['total'] / avg_df['income'])
    avg_df = avg_df[avg_df['category'] != 'income']

    fig = px.pie(avg_df, values = 'percentage', names = 'category')

    return fig

@app.callback(
    Input("profit_target", "value"),
    Input("housing_payment", "value"),
    Input("saving_months", "value"),
    Input("historical_start_year", "value"))
def accounts_table(profit_target, housing_payment, saving_months, historical_start_year):

    month_sum_df = get_month_sum_df(finance_df)

    month_sum_df = month_sum_df[month_sum_df['year'] >= historical_start_year]
    month_sum_df['free_cash'] = month_sum_df['total'] - profit_target

# html.Div([dash_table.DataTable(id='habit_tracker_scorecard', data = [])]), 

year_dropdown = dcc.Dropdown(
                    id="finance_year_dropdown",
                    options=finance_df['year'].unique(),
                    value=datetime.now().year,
                    clearable=False)

month_dropdown = dcc.Dropdown(
                    id="finance_month_dropdown",
                    options=list(range(1, 13)),
                    value=datetime.now().month,
                    clearable=False)

app.layout = dbc.Container([

    dbc.Row(
    [
        dbc.Col(html.Div(year_dropdown), width = {'size': 3 }),
        dbc.Col(html.Div(month_dropdown), width = {'size': 3 }),

        dbc.Col(
            html.Div(["Profit Target: ", dcc.Input(id='profit_target', value=3000, type='number')]),
            style = {'textAlign': 'right'},
            width = {'size': 2 }),

        dbc.Col(
            html.Div(["Housing Payment: ", dcc.Input(id='housing_payment', value=1700, type='number')]), 
            style = {'textAlign': 'right'},
            width = {'size': 2 }),

        dbc.Col(
            html.Div(["Savings (Months): ", dcc.Input(id='saving_months', value=6, type='number')]), 
            style = {'textAlign': 'right'},
            width = {'size': 2 })
    ],
        justify="evenly",
        className = 'g-0'
    ),

    dbc.Row(
    [
        dbc.Col(
            html.Div(["Historical Start Year: ", dcc.Input(id='historical_start_year', value=2019, type='number')]),
            style = {'textAlign': 'right'},
            width = {'size': 2, 'offset': 6}),
    ],
        justify="evenly",
        className = 'g-0'
    ),    

    dbc.Row(
    [
        dbc.Col(
            html.Div([dcc.Graph(id="monthly_finance_barchart")]),
            width = {'size': 6}
        ),

        dbc.Col(
            html.Div([dcc.Graph(id="avg_category_piechart")]),
            width = {'size': 6}
        )
    ],
        justify="evenly",
        className = 'g-0'
    )
],
    fluid = True
)

if __name__ == '__main__':
    app.run_server(debug=True)