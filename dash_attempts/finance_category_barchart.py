from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import pandas as pd

app = Dash(__name__)

df = pd.read_csv('./temp_cache/daily_finances.csv')

@app.callback(
    Output("graph_1", "figure"), 
    Input("month_dropdown", "value"), 
    Input("year_dropdown", "value"))
def update_bar_chart(month, year):
    
    filter_df = df[(df['year'] == year) & (df['month'] == month)].groupby('category').agg({'total': 'sum'}).reset_index(drop = False)
    
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

    return fig


def all_profit_loss_barchart():
    
    df['datetime'] = pd.to_datetime(df[['year', 'month', 'day']])
    df['quarter'] = df['datetime'].dt.quarter
    sum_df = df[df['category'] != 'bonus'].groupby(['year', 'quarter']).agg({'total': 'sum'}).reset_index(drop = False)

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

    return fig

app.layout = html.Div([
    html.Div([
        dcc.Dropdown(
            id="month_dropdown",
            options=list(range(1, 13)),
            value=df[df['year'] == max(df['year'])]['month'].max(),
            clearable=False,
            style= {'width': '50%', 'justify-content': 'center'}
        ),
        dcc.Dropdown(
            id="year_dropdown",
            #TODO need to make this dependant on data
            options=df['year'].unique(),
            value=2022,
            clearable=False,
            style= {'width': '50%', 'justify-content': 'center'}
        ),
        dcc.Graph(id="graph_1"),
        dcc.Graph(id="graph_2", figure = all_profit_loss_barchart()),
    ]), 
])

app.run_server(debug=True)