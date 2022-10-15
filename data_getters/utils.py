import os
import json
import glob
import pandas as pd

milliseconds_in_hours = 3600000
milliseconds_in_seconds = 1000

def get_latest_file(file_prefix: str):
    
    cache_dir = './temp_cache'
    files = glob.glob(f'{cache_dir}/{file_prefix}*')

    latest_date = pd.to_datetime('1/1/2019')
    for file in files:
        file_name = os.path.basename(file)
        split_filename = file_name.split('_')

        if len(split_filename) < 3:
            continue

        date = pd.to_datetime(split_filename[2].replace('.csv', ''))
        if date > latest_date:
            latest_date = date.date()
        
    file_path = [x for x in files if latest_date.strftime('%Y-%m-%d') in x]

    if len(file_path) == 0:
        raise ValueError(f'No dated file for prefix {file_prefix}!')
    
    ret_df = pd.read_csv(file_path[0], index_col = None)
    return ret_df

def get_user_config(username: str):

    config_dir = './user_config'
    user_json = os.path.join(config_dir, username + '_config.json')
    
    json_file = ''
    try:
        json_file = open(user_json)
    except FileNotFoundError:
        raise FileNotFoundError(f'User config for user name {username}. Does not exist. Please create it')

    user_config_data = json.load(json_file)
    return user_config_data
    
