import requests
import couchdb
from datetime import datetime
from itertools import repeat
import pandas as pd
import numpy as np

from utils import milliseconds_in_hours, milliseconds_in_seconds

class Marvin_Processor():

    endpoint = 'https://serv.amazingmarvin.com/api/'
    # Database access
    sync_server = 'https://512940bf-6e0c-4d7b-884b-9fc66185836b-bluemix.cloudant.com'

    #TODO put in config
    # Marvin API access
    api_token = 'xmJU2SQBDK5KWGfKDm2YQpDHmUQ='
    full_access_token = 'a0QIpNKrR1l9j8Po3CkqTt2L1v0='
    aggregate_categories = ['Orsted', 'Edison Energy', 'Music']

    sync_database = 'u391630018'
    sync_user = 'apikey-8d34200f26004b4c9646929853fdd852'
    sync_password = '92c8dbd20b1dcf2ee28c2a99508bce0d2c6446d7'

    couch = couchdb.Server(sync_server)
    couch.resource.credentials = (sync_user, sync_password)
    server_DB = couch[sync_database]

    def parse_task_duration(task):

        #If this, seems like calData may be the thing to get?
        if task.get('times') is None:
            start_time = None
            end_time = None
            duration = None
        else:
            start_time = None if len(task['times']) == 0 else \
                    pd.to_datetime(datetime.fromtimestamp(task['times'][0] / milliseconds_in_seconds))

            end_time = None if len(task['times']) == 0 else \
                pd.to_datetime(datetime.fromtimestamp(task['times'][1] / milliseconds_in_seconds))

            duration = task['duration'] / milliseconds_in_hours

        return duration, start_time, end_time

    def get_parent_list(task, categories):
        
        parent_val = [item for item in categories if item['_id'] == task['parentId']]
        
        if len(parent_val) == 0:
            return []
        
        parent = parent_val[0]
        parent_list = [parent]

        while parent['parentId'] != 'root':
            parent = [item for item in categories if item['_id'] == parent['parentId']][0]
            parent_list.append(parent)

        return parent_list

    def parse_task(task, categories):
        
        parent_list = Marvin_Processor.get_parent_list(task, categories)

        if len(parent_list) == 0:
            return pd.DataFrame()
        
        parent_sequence = '/'.join([o['title'] for o in parent_list])
        
        duration, start_time, end_time = Marvin_Processor.parse_task_duration(task)

        time_estimate = task.get('timeEstimate')
        time_estimate = None if time_estimate is None else time_estimate / milliseconds_in_hours

        return pd.DataFrame(data = {
                'name': [task['title']],
                'day': [task['day']],
                'time_estimate': [time_estimate],
                'parent': [parent_sequence],
                'category': [parent_list[-1]['title']],
                'start_time': [start_time],
                'end_time': [end_time],
                'duration': [duration]
        })

    def format_task_df(task_df: pd.DataFrame):
        
        task_df = task_df[task_df['day'] != 'unassigned']
        task_df['day'] = pd.to_datetime(task_df['day'])
        task_df['month'] = task_df['day'].dt.month
        task_df['year'] = task_df['day'].dt.year

        task_df[['sub_project_2', 'sub_project', 'main_category', 'main_category_dupe']] = task_df['parent'].str.split('/', expand = True)
        
        task_df['end_val'] = np.where(
            task_df['category'].isin(Marvin_Processor.aggregate_categories), 
            task_df['category'], 
            task_df['sub_project_2'])

        task_df.drop(columns = {'main_category_dupe', 'category', 'sub_project', 'sub_project_2', 'parent'}, inplace=True)
        task_df.rename(columns = {'end_val': 'category'}, inplace=True)

        return task_df

    def get_task_df():

        categories = list(Marvin_Processor.server_DB.find({'selector': {'db': 'Categories'}}))
        all_tasks = Marvin_Processor.server_DB.find({'selector': {'db': 'Tasks'}})

        task_df = pd.concat(map(Marvin_Processor.parse_task, all_tasks, repeat(categories)))
        task_df = task_df[task_df['day'] != 'unassigned']

        date_str = datetime.now().strftime('%Y-%m-%d')
        task_df.to_csv(f'./temp_cache/marvin_tasks_{date_str}.csv', index=False)