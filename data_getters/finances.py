#curl.exe -X  POST "http://127.0.0.1:8000/get_historical_data?user_name=jjm&read_cache=true&write_cache=true"

import os
import pandas as pd
import requests

def get_mint_historical_data(read_cache = True, user_name = 'jjm'):
    method = 'get_historical_by_category'
    api_server_url = 'http://127.0.0.1:8000/'

    url = api_server_url + method + f'?user_name={user_name}&read_cache={read_cache}&write_cache=False'
    response = requests.post(url, verify=False)

    ret_df = pd.DataFrame(response.json())
    ret_df.rename(columns = {'Year': 'year', 'Month': 'month', 'Day': 'day'}, inplace=True)
    ret_df['timestamp'] = pd.to_datetime(ret_df[['year', 'month', 'day']])

    date_str = ret_df['timestamp'].max().date()
    ret_df.to_csv(f'./temp_cache/daily_finances_{date_str}.csv')
    return ret_df

if __name__ == '__main__':
    get_mint_historical_data(read_cache=False)