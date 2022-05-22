import flask
from dash import Dash, html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from datetime import datetime

from data_getters.utils import get_latest_file
from data_getters.finances import get_month_sum_df

server = flask.Flask(__name__)
app = Dash(__name__, server = server, external_stylesheets=[dbc.themes.BOOTSTRAP])

finance_df = get_latest_file(file_prefix = 'daily_finances')
account_df = get_latest_file(file_prefix = 'account_totals')

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
    Output("savings_line_plot", "figure"),
    Input("profit_target", "value"),
    Input("historical_start_year", "value"))
def savings_line_plot(monthly_saving_target, historical_start_year):

    month_sum_df = get_month_sum_df(finance_df)
    month_sum_df = month_sum_df[month_sum_df['year'] >= historical_start_year]
    month_sum_df['day'] = 1
    month_sum_df['datetime'] = pd.to_datetime(month_sum_df[['year', 'month', 'day']])

    fig = px.line(month_sum_df, x = 'datetime', y= 'total')
    fig.add_shape(
        type='line',
        x0 = month_sum_df['datetime'].min(),
        y0 = int(monthly_saving_target),
        x1 = month_sum_df['datetime'].max(),
        y1 = int(monthly_saving_target),
        line = dict(color='Black',),
        xref = 'x',
        yref = 'y')

    monthly_income = finance_df[
        (finance_df['month'] == month_sum_df['datetime'].max().month - 1) & 
        (finance_df['year'] == month_sum_df['datetime'].max().year) & 
        (finance_df['category'] == 'income')]['total'].sum()

    avg_spend = finance_df[
        (finance_df['year'] >= historical_start_year) & 
        ~(finance_df['category'].isin(['income', 'bonus']))] \
        .groupby(['year', 'month']).agg({'total': 'sum'}).reset_index(drop = False)['total'].mean()

    shortfall = (avg_spend + monthly_income) - monthly_saving_target

    fig.add_annotation(
        x = month_sum_df['datetime'].median(), 
        y = month_sum_df['total'].max() * 1.1,
        text = f"Avg. profit diff: ${int(round(shortfall, -1))}",
        showarrow = False,    
        font = dict(size=18),
        yshift = 0)

    return fig

@app.callback(
    Output("spending_line_plot", "figure"),
    Input("profit_target", "value"),
    Input("historical_start_year", "value"))
def spending_line_plot(profit_target, historical_start_year):

    month_spend_df = finance_df[
        (finance_df['year'] >= historical_start_year) & 
        ~(finance_df['category'].isin(['income', 'bonus']))] \
        .groupby(['year', 'month']).agg({'total': 'sum'}).reset_index(drop = False)

    month_spend_df['day'] = 1
    month_spend_df['datetime'] = pd.to_datetime(month_spend_df[['year', 'month', 'day']])

    monthly_income = finance_df[
        (finance_df['month'] == month_spend_df['datetime'].max().month - 1) & 
        (finance_df['year'] == month_spend_df['datetime'].max().year) & 
        (finance_df['category'] == 'income')]['total'].sum()
        
    monthly_spending_target = (monthly_income - profit_target) * -1
    avg_spending_diff = month_spend_df['total'].mean() - monthly_spending_target
    fig = px.line(month_spend_df, x = 'datetime', y= 'total')

    fig.add_shape(
        type='line',
        x0 = month_spend_df['datetime'].min(),
        y0 = int(monthly_spending_target),
        x1 = month_spend_df['datetime'].max(),
        y1 = int(monthly_spending_target),
        line = dict(color='Black',),
        xref = 'x',
        yref = 'y')

    fig.add_annotation(
        x = month_spend_df['datetime'].median(), 
        y = month_spend_df['total'].max() * 1.1,
        text = f"Avg. spending diff: ${int(round(avg_spending_diff, -1))}",
        showarrow = False,    
        font = dict(size=18),
        yshift = 0)


    return fig

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
        'budget': [housing_payment * 1.05, -400, -750]
    })

    filter_df = filter_df.merge(general_budget, how = 'left', on = 'category')

    housing_adder = housing_payment - filter_df[filter_df['category'] == 'housing']['total'].sum()
    sum_df = pd.DataFrame(data = {
        'year': [year],
        'month': [month],
        'category': 'profit/loss',
        'budget': [profit_target],
        'total': [filter_df['total'].sum() + housing_adder]
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
    Input("housing_payment", "value"),
    Input("historical_start_year", "value"))
def avg_category_piechart(housing_payment, historical_start_year):
    
    month_sum_df = get_month_sum_df(finance_df)

    month_sum_df = month_sum_df[month_sum_df['year'] >= historical_start_year]

    month_sum_df = pd.melt(month_sum_df, id_vars = ['year', 'month'], value_vars = ['total'])
    month_sum_df.rename(columns = {'variable': 'category', 'value': 'total'}, inplace = True)
    month_sum_df.loc[month_sum_df['category'] == 'total', ['category']] = 'saving'

    historical_df = finance_df[
        (finance_df['year'] >= historical_start_year) & 
        ~((finance_df['year'] == datetime.now().year) & (finance_df['month'] == datetime.now().month))]

    avg_df = historical_df \
        .groupby(['year', 'month', 'category']).agg({'total': 'sum'}) \
        .groupby(['category']).agg({'total': 'mean'}).reset_index(drop = False)
    
    housing_adder = housing_payment - avg_df[avg_df['category'] == 'housing']['total'].sum()
    avg_savings = month_sum_df[month_sum_df['category'] == 'saving']['total'].mean() + housing_adder

    avg_df = avg_df[~(avg_df['category'].isin(['bonus', 'loans', 'music']))]
    avg_df.loc[avg_df['category'] == 'housing', ['total']] = housing_payment

    avg_df = pd.concat([avg_df, pd.DataFrame(data = {'category': ['savings'], 'total': [avg_savings] })])
    avg_df['total'] = abs(avg_df['total'])
    avg_df = avg_df[avg_df['category'] != 'income']

    fig = px.pie(avg_df, values = 'total', names = 'category')

    return fig

@app.callback(
    Output("accounts_table", "data"),
    Output("accounts_table", "columns"), 
    Input("profit_target", "value"),
    Input("housing_payment", "value"),
    Input("saving_months", "value"),
    Input("historical_start_year", "value"))
def accounts_table(profit_target, housing_payment, saving_months, historical_start_year):

    month_sum_df = get_month_sum_df(finance_df)

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
    
    final_df['total'] =  round(final_df['value'], -1)
    final_df.drop(columns = ['value'], inplace = True)
    final_df = final_df.apply(lambda x: [f'${y:,.0f}'for y in x] if x.name=='total' else x)

    return final_df.to_dict('records'), [{"name": i, "id": i} for i in final_df.columns]

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
    app.run_server(debug=True)