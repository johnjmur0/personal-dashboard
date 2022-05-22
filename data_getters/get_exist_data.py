import os
import math
import pandas as pd
import numpy as np
import requests
from datetime import datetime

from utils import get_user_config

class Exist_Processor():

    exist_server_url = 'https://exist.io/api/1/'
    attributes_endpoint = 'users/$self/attributes'
    
    def get_login_credentials(user_config: dict):

        return { 
            'username': user_config['exist_config']['username'], 
            'password': user_config['exist_config']['password'] 
        }             

    def get_token_header(login_dict: dict):

        token_endpoint = 'auth/simple-token/'

        token_url = Exist_Processor.exist_server_url + token_endpoint
        response = requests.post(token_url, data = login_dict, verify = False)
        token = response.json()['token']
        token_header = {'Authorization': 'Token ' + token }
        token_response = requests.get(Exist_Processor.exist_server_url + 'users/$self/today/', headers = token_header)

        assert token_response == 200

        return token_header

    def get_date_range():

        start_date = pd.to_datetime('2021-12-01')
        end_date = datetime.now()

        month_duration = math.ceil((end_date - start_date) / np.timedelta64(1, 'M'))
        return pd.date_range(start = start_date, freq = 'M', periods = month_duration)

    def get_attributes_df(date_range: pd.date_range, login_dict: dict):

        attributes_df = pd.DataFrame()

        token_header = Exist_Processor.get_token_header(login_dict)

        for date in date_range:
            
            date_str = str(date).split(' ')[0]
            count = date.daysinmonth

            date_params = f'?limit={count}&date_max={date_str}'
            
            request_str = Exist_Processor.exist_server_url + Exist_Processor.attributes_endpoint + date_params
            attributes_response = requests.get(request_str, headers = token_header)

            response_df = pd.DataFrame(attributes_response.json())
            attributes_df = pd.concat([attributes_df, response_df])

        ret_df = pd.DataFrame()
        for index, row in attributes_df.iterrows():

            df = pd.DataFrame(row['values'])
            df['attribute'] = row['attribute']
            ret_df = pd.concat([ret_df, df])

        return ret_df

    def get_latest_data(username: str):

        user_config = get_user_config(username)
        login_dict = Exist_Processor.get_login_credentials(user_config)

        exist_df = Exist_Processor.get_attributes_df(Exist_Processor.get_date_range(), login_dict)
        
        date_str = exist_df['date'].max()
        exist_df.to_csv(f'./temp_cache/exist_data_{date_str}.csv')

class Exist_Dashboard_Helpers():

    def format_exist_df(exist_df: pd.DataFrame, user_config: dict):
        
        key_habits_df = pd.DataFrame(data = user_config['exist_config']['key_habits'], index = [0]).T.reset_index(drop = False) \
            .rename(columns = {'index': 'attribute', 0: 'value'})  
        
        habit_df = exist_df[exist_df['attribute'].isin(key_habits_df)].astype({'value': 'float64'}) \
            .merge(key_habits_df, on='attribute', how='left')

        habit_df['value'] = np.where(habit_df['attribute'] == 'sleep_start', ((habit_df['value'] / 60) + 12) % 24, habit_df['value'])
        habit_df['value'] = np.where(habit_df['attribute'] == 'sleep_end', habit_df['value'] / 60, habit_df['value'])

        habit_df['achieved'] = np.where(
            habit_df['attribute'].isin(['sleep_start', 'sleep_end']), 
            habit_df['value'] <= habit_df['success'], 
            habit_df['value'] >= habit_df['success'])

        habit_df['date'] = pd.to_datetime(habit_df['date'])
        habit_df[['year', 'month']] = [habit_df['date'].dt.year, habit_df['date'].dt.month]

        return habit_df
