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

finance_df = pd.read_csv('./temp_cache/daily_finances.csv', index_col=None)
task_df = pd.read_csv('./temp_cache/marvin_tasks.csv', index_col=None)
exist_df = pd.read_csv('./temp_cache/exist_data.csv', index_col=None)

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
    grouped_df = filtered_df.groupby(['parent', 'category', 'year', 'month']).agg({'duration': 'sum'}).reset_index(drop = False)

    if grouped_df['duration'].sum() == 0:
        grouped_df = pd.DataFrame()
    else:
        grouped_df[['sub-project_2', 'sub-project_1', 'project', 'category_dupe']] = grouped_df['parent'].str.split('/', expand = True)
        grouped_df.drop(columns = {'category_dupe', 'parent'}, inplace=True)

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
                style= {'width': '50%', 'display': 'inline-block', 'float': 'left'}
            ),
        ]),

        html.Div([

            dcc.Dropdown(
                id="finance_month_dropdown",
                options=list(range(1, 13)),
                value=datetime.now().month,
                clearable=False,
                style= {'width': '50%', 'display': 'inline-block', 'float': 'right'}
            ),
        ]),
    ],
        style = {'display': 'flex'}
    ),

    html.Div([
        dash_table.DataTable(id='habit_tracker_scorecard', data = []),
    ], 
        style = {'width': '50%', 'display': 'inline-block', 'float': 'left', 'marginTop': 0}
    ), 

    html.Div([
        dcc.Graph(id="monthly_finance_barchart"),
    ],
        style = {'width': '50%', 'display': 'inline-block', 'float': 'right', 'marginTop': -100}
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