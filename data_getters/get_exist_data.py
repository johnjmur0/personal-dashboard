import os
import math
import pandas as pd
import numpy as np
import requests
from datetime import datetime

class Exist_Processor():

    exist_server_url = 'https://exist.io/api/1/'
    attributes_endpoint = 'users/$self/attributes'
    #TODO put in config
    
    login = {'username': 'johnjmur0', 'password': 'HuLP5h$k@5wg'}
    
    key_habits = pd.DataFrame( data = {
            'attribute': ['exercise', 'sleep_start', 'sleep_end', 'steps', 'free_in_am', 'got_outside', 'read', 'mood'],
            'success': [1, 10.5, 7.5, 4000, 1, 1, 1, 6]
        })

    def send_simple_request():

        token_endpoint = 'auth/simple-token/'

        token_url = Exist_Processor.exist_server_url + token_endpoint
        response = requests.post(token_url, data = Exist_Processor.login, verify = False)
        token = response.json()['token']
        token_header = {'Authorization': 'Token ' + token }
        token_response = requests.get(Exist_Processor.exist_server_url + 'users/$self/today/', headers = token_header)

        assert token_response == 200

    def get_date_range():

        start_date = pd.to_datetime('2021-12-01')
        end_date = datetime.now()

        month_duration = math.ceil((end_date - start_date) / np.timedelta64(1, 'M'))
        return pd.date_range(start = start_date, freq = 'M', periods = month_duration)

    def get_attributes_df(date_range):

        attributes_df = pd.DataFrame()

        for date in date_range:
            
            date_str = str(date).split(' ')[0]
            count = date.daysinmonth

            date_params = f'?limit={count}&date_max={date_str}'
            
            request_str = Exist_Processor.exist_server_url + Exist_Processor.attributes_endpoint + date_params
            attributes_response = requests.get(request_str, headers = Exist_Processor.token_header)

            response_df = pd.DataFrame(attributes_response.json())
            attributes_df = pd.concat([attributes_df, response_df])

        ret_df = pd.DataFrame()
        for index, row in attributes_df.iterrows():

            df = pd.DataFrame(row['values'])
            df['attribute'] = row['attribute']
            ret_df = pd.concat([ret_df, df])

        date_str = ret_df['date'].max()
        ret_df.to_csv(f'./temp_cache/exist_data_{date_str}.csv')

        return ret_df

    def format_exist_df(exist_df):
        
        habit_df = exist_df[exist_df['attribute'].isin(Exist_Processor.key_habits['attribute'])]
        habit_df = habit_df.astype({'value': 'float64'})
        habit_df = habit_df.merge(Exist_Processor.key_habits, on='attribute', how='left')

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

    def get_latest_data():

        Exist_Processor.send_simple_request()
        exist_df = Exist_Processor.get_attributes_df(Exist_Processor.get_date_range())
        return Exist_Processor.format_exist_df(exist_df)