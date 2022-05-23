import sys  
import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from datetime import datetime

from data_getters.utils import get_latest_file, get_user_config
from data_getters.finances import Finances_Dashboard_Helpers

server = flask.Flask(__name__)
app = Dash(__name__, server = server, external_stylesheets=[dbc.themes.BOOTSTRAP])

def line_plot_base(input_df: pd.DataFrame, yintercept_val: int, shortfall_val: int):

    fig = px.line(input_df, x = 'datetime', y= 'total')
    
    fig.add_shape(
        type='line', 
        line = dict(color='Black',),
        x0 = input_df['datetime'].min(), 
        y0 = int(yintercept_val),
        x1 = input_df['datetime'].max(), 
        y1 = int(yintercept_val),
        xref = 'x', 
        yref = 'y')

    fig.add_annotation(
        x = input_df['datetime'].median(), 
        y = input_df['total'].max() * 1.1,
        text = f"Avg. shortfall: ${int(round(shortfall_val, -1))}",
        showarrow = False,    
        font = dict(size=18),
        yshift = 0)

    fig.update_layout(
        margin=dict(l = 10, r = 10, t = 50, b = 10), 
        yaxis_title=None, 
        xaxis_title=None)

    return fig
    
@app.callback(
    Output("savings_line_plot", "figure"),
    Input("profit_target", "value"),
    Input("historical_start_year", "value"))
def savings_line_plot(profit_target: int, historical_start_year: int):

    graph_df = month_sum_df[month_sum_df['year'] >= historical_start_year]

    most_recent_obs = graph_df['datetime'].max()

    shortfall_val = Finances_Dashboard_Helpers.get_budget_shortfall(
        finance_df, 
        profit_target, 
        most_recent_obs.month - 1, 
        most_recent_obs.year, 
        historical_start_year)

    return line_plot_base(graph_df, profit_target, shortfall_val)

@app.callback(
    Output("spending_line_plot", "figure"),
    Input("profit_target", "value"),
    Input("historical_start_year", "value"))
def spending_line_plot(profit_target: int, historical_start_year: int):

    graph_df = finance_df[
        (finance_df['year'] >= historical_start_year) & 
        ~(finance_df['category'].isin(['income', 'bonus']))] \
        .groupby(['year', 'month']).agg({'total': 'sum'}).reset_index(drop = False)

    graph_df['day'] = 1
    graph_df['datetime'] = pd.to_datetime(graph_df[['year', 'month', 'day']])

    most_recent_obs = graph_df['datetime'].max()

    monthly_income = Finances_Dashboard_Helpers.get_monthly_income(
        finance_df, 
        most_recent_obs.month - 1, 
        most_recent_obs.year)

    monthly_spending_target = (monthly_income - profit_target) * -1
    avg_spending_diff = graph_df['total'].mean() - monthly_spending_target

    return line_plot_base(graph_df, monthly_spending_target, avg_spending_diff)

@app.callback(
    Output("monthly_finance_barchart", "figure"), 
    Input("finance_month_dropdown", "value"), 
    Input("finance_year_dropdown", "value"),
    Input("profit_target", "value"),
    Input("housing_payment", "value"))
def monthly_finance_barchart(month: int, year: int, profit_target: int, housing_payment: int):
    
    filter_df = Finances_Dashboard_Helpers.create_spend_budget_df(
        finance_df, 
        budget_df, 
        year, 
        month,
        housing_payment,
        profit_target)

    fig = px.bar(
        filter_df, 
        x='category', 
        y='value', 
        color='variable', 
        barmode = 'group', 
        text_auto = '.2s', 
        color_discrete_sequence = ['blue', 'grey'])

    fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    fig.update_layout(
        margin=dict(r = 0, l = 0), 
        yaxis_title=None, 
        xaxis_title = None)

    return fig

@app.callback(
    Output("avg_category_piechart", "figure"), 
    Input("housing_payment", "value"),
    Input("historical_start_year", "value"))
def avg_category_piechart(housing_payment: int, historical_start_year: int):

    graph_df = month_sum_df[month_sum_df['year'] >= historical_start_year]

    graph_df = pd.melt(graph_df, id_vars = ['year', 'month'], value_vars = ['total'])
    graph_df.rename(columns = {'variable': 'category', 'value': 'total'}, inplace = True)
    graph_df.loc[graph_df['category'] == 'total', 'category'] = 'saving'

    historical_df = finance_df[
        (finance_df['year'] >= historical_start_year) & 
        ~((finance_df['year'] == datetime.now().year) & 
            (finance_df['month'] == datetime.now().month))]

    avg_df = historical_df \
        .groupby(['year', 'month', 'category']).agg({'total': 'sum'}) \
        .groupby(['category']).agg({'total': 'mean'}).reset_index(drop = False)
    
    housing_adder = housing_payment - avg_df[avg_df['category'] == 'housing']['total'].sum()
    avg_savings = graph_df[graph_df['category'] == 'saving']['total'].mean() + housing_adder

    avg_df = avg_df[~(avg_df['category'].isin(['bonus', 'loans', 'music']))]
    avg_df.loc[avg_df['category'] == 'housing', ['total']] = housing_payment

    avg_df = pd.concat([avg_df, pd.DataFrame(data = {'category': ['savings'], 'total': [avg_savings] })])
    avg_df['total'] = abs(avg_df['total'])
    avg_df = avg_df[avg_df['category'] != 'income']

    return px.pie(avg_df, values = 'total', names = 'category')

@app.callback(
    Output("accounts_table", "data"),
    Output("accounts_table", "columns"), 
    Input("profit_target", "value"),
    Input("housing_payment", "value"),
    Input("saving_months", "value"),
    Input("historical_start_year", "value"))
def accounts_table(profit_target: int, housing_payment: int, saving_months: int, historical_start_year: int):

    month_sum_df = Finances_Dashboard_Helpers.get_month_sum_df(finance_df)

    month_sum_df = month_sum_df[month_sum_df['year'] >= historical_start_year]
    month_sum_df['free_cash'] = month_sum_df['total'] - profit_target

    pivot_account_df = pd.pivot_table(account_df[['account_type', 'total']], values = 'total', columns = ['account_type'])
    pivot_account_df['bank'] = pivot_account_df['bank'] + pivot_account_df['credit']
    pivot_account_df.drop(columns = ['credit', 'loan'], inplace = True)
    
    avg_spend_df = finance_df[finance_df['year'] >= historical_start_year] \
        .groupby(['year', 'month', 'category']).agg({'total': 'sum'}) \
        .groupby(['category']).agg({'total': 'mean'}).reset_index(drop = False)
    
    avg_spend_df = avg_spend_df[~avg_spend_df['category'].isin(['loans', 'housing', 'bonus'])]

    monthly_df = avg_spend_df[avg_spend_df['category'].isin(['income', 'investments'])].pivot_table(values = 'total', columns = 'category')\
        .reset_index(drop = True)
        
    monthly_df['spending'] = avg_spend_df.loc[avg_spend_df['category'].isin(['discretionary', 'groceries']), ['total']].sum()[0]

    monthly_df['housing'] = housing_payment
    monthly_df['savings'] = monthly_df['income'] + monthly_df['spending'] + monthly_df['investments'] + monthly_df['housing']

    final_df = pd.concat([pivot_account_df.reset_index(drop = True), monthly_df.reset_index(drop = True)], axis = 1)

    final_df['cash savings'] = (final_df['housing'] + final_df['spending'] + final_df['investments']) * saving_months * -1
    final_df['excess savings'] = final_df['bank'] - final_df['cash savings']

    final_cols = ['bank', 'investment', 'cash savings', 'excess savings', 'income', 'spending', 'housing', 'savings',  'investments']
    final_df = pd.melt(final_df, id_vars = [], value_vars = final_cols)
    
    final_df['total'] = round(final_df['value'], -1)
    final_df.drop(columns = ['value'], inplace = True)
    final_df = final_df.apply(lambda x: [f'${y:,.0f}'for y in x] if x.name=='total' else x)

    return final_df.to_dict('records'), [{"name": i, "id": i} for i in final_df.columns]

def year_dropdown():
    
    return dcc.Dropdown(
        id="finance_year_dropdown",
        options=list(range(datetime.now().year - 4, datetime.now().year + 1)),
        value=datetime.now().year,
        clearable=False)

def month_dropdown():
    return dcc.Dropdown(
        id="finance_month_dropdown",
        options=list(range(1, 13)),
        value=datetime.now().month,
        clearable=False)

app.layout = dbc.Container([

    dbc.Row(
    [
        dbc.Col(html.Div(year_dropdown()), width = {'size': 3 }),
        dbc.Col(html.Div(month_dropdown()), width = {'size': 3 }),
    ],
        justify="start",
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
        justify="evenly"
    ),

    dbc.Row(
        [
            dbc.Col(
                html.Div(["Savings (Months): ", dcc.Input(id='saving_months', value=8, type='number')]), 
                style = {'textAlign': 'right'},
                width = {'size': 2 }),

            dbc.Col(
                html.Div(["Historical Start Year: ", dcc.Input(id='historical_start_year', value=2019, type='number')]),
                style = {'textAlign': 'right'},
                width = {'size': 2 }),

            dbc.Col(
                html.Div(["Profit Target: ", dcc.Input(id='profit_target', value=3000, type='number', step = 100)]),
                style = {'textAlign': 'right'},
                width = {'size': 2 }),

        dbc.Col(
            html.Div(["Housing Payment: ", dcc.Input(id='housing_payment', value=-1700, type='number', step = 100)]), 
            style = {'textAlign': 'right'},
            width = {'size': 2 })
        ],
        className = 'g-0',
        align = 'center',
        justify = 'evenly'
    ),

    dbc.Row(
    [
        dbc.Col(
            html.Div([dash_table.DataTable(id = 'accounts_table', data = [])]),
            width = {'size': 2 }
        ),

        dbc.Col(
            html.Div([dcc.Graph(id="savings_line_plot")]),
            width = {'size': 5 }
        ),

        dbc.Col(
            html.Div([dcc.Graph(id="spending_line_plot")]),
            width = {'size': 5 }
        )
    ],
        justify = "evenly",
        align = 'center',
        className = 'g-0'
    )
],
    fluid = True
)

if __name__ == '__main__':
    
    user_name = 'jjm' #sys.argv[1]
    user_config = get_user_config(user_name)
    
    budget_df = Finances_Dashboard_Helpers.get_general_budget(user_config)
    
    finance_df = get_latest_file(file_prefix = 'daily_finances')
    month_sum_df = Finances_Dashboard_Helpers.get_month_sum_df(finance_df)
    account_df = get_latest_file(file_prefix = 'account_totals')

    app.run_server(debug=True)