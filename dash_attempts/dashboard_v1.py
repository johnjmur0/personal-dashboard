from operator import index
import os
import glob
from sys import prefix
from dash import Dash, html, dcc, Input, Output, dash_table
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime

app = Dash(__name__)

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
        
    print (latest_date)
    file_path = [x for x in files if latest_date.strftime('%Y-%m-%d') in x]

    if len(file_path) == 0:
        raise ValueError(f'No dated file for prefix {file_prefix}!')
    
    ret_df = pd.read_csv(file_path[0], index_col = None)
    print (ret_df.head())
    return ret_df
    
finance_df = get_latest_file(file_prefix = 'daily_finances')
task_df = get_latest_file(file_prefix = 'marvin_tasks')
exist_df = get_latest_file(file_prefix = 'exist_data')

key_habits = pd.DataFrame( data = {
        'attribute': ['exercise', 'sleep_start', 'sleep_end', 'steps', 'free_in_am', 'got_outside', 'read', 'mood'],
        'success': [1, 10.5, 7.5, 4000, 1, 1, 1, 6]
    })

task_df = format_task_df(task_df)
habit_df = format_exist_df(exist_df, key_habits)

@app.callback(
    Output("monthly_finance_barchart", "figure"), 
    Input("finance_month_dropdown", "value"), 
    Input("finance_year_dropdown", "value"))
def monthly_finance_barchart(month, year):
    
    filter_df = finance_df[(finance_df['year'] == year) & (finance_df['month'] == month)].groupby('category').agg({'total': 'sum'}).reset_index(drop = False)
    
    sum_df = pd.DataFrame(data = {
        'year': [year],
        'month': [month],
        'category': 'profit/loss',
        'total': [filter_df['total'].sum()]
    })

    filter_df = pd.concat([filter_df, sum_df])
    
    filter_df = filter_df[abs(filter_df['total']) > 100]

    fig = px.bar(filter_df, x='category', y='total', text_auto = '.2s')
    fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    fig.update_layout(yaxis_title=None, xaxis_title = None)

    return fig

@app.callback(
    Output("total_free_cash", "children"), 
    Input("finance_month_dropdown", "value"), 
    Input("finance_year_dropdown", "value"),
    Input("savings_target", "value"))
def total_free_cash(month, year, monthly_saving_target):
    
    month_sum_df = finance_df[~finance_df['category'].isin(['bonus', 'investment'])].groupby(['year', 'month']).agg({'total': 'sum'}).reset_index(drop = False)
    month_sum_df['free_cash'] = month_sum_df['total'] - monthly_saving_target

    month_sum_df = month_sum_df[~(month_sum_df['month'] != month) & (month_sum_df['year'] != year)]

    return f'Free cash flow: {int(round(month_sum_df["free_cash"].sum(), -2))}'

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
    Output("monthly_task_piechart", "figure"), 
    Input("finance_month_dropdown", "value"), 
    Input("finance_year_dropdown", "value"))
def task_duration_piechart(month, year):

    filtered_df = task_df[(task_df['year'] == year) & (task_df['month'] == month)] 
    grouped_df = filtered_df.groupby(['category', 'year', 'month']).agg({'duration': 'sum'}).reset_index(drop = False)

    if grouped_df['duration'].sum() == 0:
        grouped_df = pd.DataFrame()

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
    daily_total_df['month_days'] = daily_total_df['datetime'].dt.daysinmonth

    display_df = daily_total_df[['attribute', 'achieved', 'month_days']]
    return display_df.to_dict('records'), [{"name": i, "id": i} for i in display_df.columns]

app.layout = html.Div([

    html.Div([

        html.Div([
            dcc.Dropdown(
                id="finance_year_dropdown",
                options=finance_df['year'].unique(),
                value=datetime.now().year,
                clearable=False,
            ),
        ],
            style= {'width': '25%', 'display': 'inline-block', 'float': 'left'}
        ),

        html.Div([

            dcc.Dropdown(
                id="finance_month_dropdown",
                options=list(range(1, 13)),
                value=datetime.now().month - 1,
                clearable=False,
            ),
        ],
            style= {'width': '25%', 'display': 'inline-block', 'float': 'right'}
        ),
    ],
        style = {'display': 'flex'}
    ),

    html.Div([
        "Savings Target: ",
        dcc.Input(id='savings_target', value=3000, type='number')
    ],
        style= {'width': '25%', 'display': 'inline-block', 'float': 'left'}    
    ),

    html.Div(id='total_free_cash'),

    html.Div([
        dash_table.DataTable(id='habit_tracker_scorecard', data = []),
    ], 
        style = {'width': '50%', 'marginTop': 50}
    ), 

    html.Div([
        dcc.Graph(id="monthly_finance_barchart"),
    ],
        style = {'width': '50%', 'display': 'inline-block', 'float': 'right', 'marginTop': -330}
    ),
    
    html.Div([
        dcc.Graph(id="monthly_task_piechart"),
    ], 
        style = {'width': '50%', 'display': 'inline-block', 'float': 'left', 'marginTop': 0}
    ), 

    html.Div([
        dcc.Graph(id="all_profit_loss_barchart", figure = all_profit_loss_barchart()),
    ],
        style = {'width': '50%', 'display': 'inline-block', 'float': 'right', 'marginTop': -50}
    ),  
])

app.run_server(debug=True)