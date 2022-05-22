#curl.exe -X  POST "http://127.0.0.1:8000/get_historical_data?user_name=jjm&read_cache=true&write_cache=true"

import os
import datetime
import pandas as pd
import requests

class Finances_Processor():

    #TODO put in config file (housing param makes it annoying). Ideally I could get from Mint
    #TODO handle bills with housing actually
    def get_general_budget(housing_payment: int):
        
        return pd.DataFrame(data = {
            'category': ['housing', 'groceries', 'discretionary'],
            'budget': [housing_payment * 1.05, -400, -750]
        })
    
    def send_finance_request_generic(method: str, user_name: str, read_cache: bool = False):

        api_server_url = 'http://127.0.0.1:8000/'

        url = api_server_url + method + f'?user_name={user_name}&read_cache={read_cache}&write_cache=False'
        response = requests.post(url, verify=False)

        if response.status_code == 500:
            #TODO figure out why this always fails the first time
            if 'rpytools' in response.text:
                response = requests.post(url, verify=False)

        ret_df = pd.DataFrame(response.json())

        return ret_df

    def get_mint_historical_data(user_name: str, read_cache: bool = True):
        
        method = 'get_historical_by_category'
        
        ret_df = Finances_Processor.send_finance_request_generic(method, user_name, read_cache)
        ret_df['timestamp'] = pd.to_datetime(ret_df[['year', 'month', 'day']])

        date_str = ret_df['timestamp'].max().date()
        ret_df.to_csv(f'./temp_cache/daily_finances_{date_str}.csv')
        return ret_df

    def get_current_accounts(user_name: str):
        
        method = 'get_current_accounts'
        ret_df = Finances_Processor.send_finance_request_generic(method, user_name, read_cache = False)

        ret_df.rename(columns = {'accountType': 'account_type',  'Total': 'total'}, inplace = True)
        date_str = datetime.datetime.now().date()
        ret_df.to_csv(f'./temp_cache/account_totals_{date_str}.csv')
        return ret_df

    def get_month_sum_df(finance_df: pd.DataFrame):
        
        regular_finances = finance_df[~finance_df['category'].isin(['bonus', 'investment'])]
        month_sum_df = regular_finances.groupby(['year', 'month']).agg({'total': 'sum'}).reset_index(drop = False)

        month_sum_df['day'] = 1
        month_sum_df['datetime'] = pd.to_datetime(month_sum_df[['year', 'month', 'day']])

        return month_sum_df