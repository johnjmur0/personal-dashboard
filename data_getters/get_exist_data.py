import os
import math
import pandas as pd
import numpy as np
import requests
from datetime import datetime

exist_server_url = 'https://exist.io/api/1/'
token_endpoint = 'auth/simple-token/'
#TODO put in config
login = {'username': 'johnjmur0', 'password': 'HuLP5h$k@5wg'}

start_date = pd.to_datetime('2021-12-01')
end_date = datetime.now()

month_duration = math.ceil((end_date - start_date) / np.timedelta64(1, 'M'))
date_range = pd.date_range(start = start_date, freq = 'M', periods = month_duration)

token_url = exist_server_url + token_endpoint
response = requests.post(token_url, data = login, verify = False)
token = response.json()['token']
token_header = {'Authorization': 'Token ' + token }
token_response = requests.get(exist_server_url + 'users/$self/today/', headers = token_header)

attributes_endpoint = 'users/$self/attributes'

attributes_df = pd.DataFrame()

for date in date_range:
    date_str = str(date).split(' ')[0]
    count = date.daysinmonth
    date_params = f'?limit={count}&date_max={date_str}'
    attributes_response = requests.get(exist_server_url + attributes_endpoint + date_params, headers = token_header)
    response_df = pd.DataFrame(attributes_response.json())
    attributes_df = pd.concat([attributes_df, response_df])

ret_df = pd.DataFrame()
for index, row in attributes_df.iterrows():

    df = pd.DataFrame(row['values'])
    df['attribute'] = row['attribute']
    ret_df = pd.concat([ret_df, df])

date_str = ret_df['date'].max()
ret_df.to_csv(f'./temp_cache/exist_data_{date_str}.csv')

print (ret_df)