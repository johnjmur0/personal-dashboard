import os
import pandas as pd
import requests

exist_server_url = 'https://exist.io/api/1/'
token_endpoint = 'auth/simple-token/'
#TODO put in config
login = {'username': 'johnjmur0', 'password': 'HuLP5h$k@5wg'}

token_url = exist_server_url + token_endpoint
response = requests.post(token_url, data = login, verify = False)
token = response.json()['token']
token_header = {'Authorization': 'Token ' + token }
token_response = requests.get(exist_server_url + 'users/$self/today/', headers = token_header)

attributes_endpoint = 'users/$self/attributes'
date_params = '?limit=31&date_max=2022-02-28'
attributes_response = requests.get(exist_server_url + attributes_endpoint + date_params, headers = token_header)

attributes_df = pd.DataFrame(attributes_response.json())

ret_df = pd.DataFrame()

for index, row in attributes_df.iterrows():

    df = pd.DataFrame(row['values'])
    df['attribute'] = row['attribute']
    ret_df = pd.concat([ret_df, df])