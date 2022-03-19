import requests
import couchdb
from datetime import datetime
from itertools import repeat
import pandas as pd
import time

milliseconds_in_hours = 3600000
milliseconds_in_seconds = 1000

endpoint = 'https://serv.amazingmarvin.com/api/'

# Marvin API access
apiToken = 'xmJU2SQBDK5KWGfKDm2YQpDHmUQ='
fullAccessToken = 'a0QIpNKrR1l9j8Po3CkqTt2L1v0='

# Database access
syncServer = 'https://512940bf-6e0c-4d7b-884b-9fc66185836b-bluemix.cloudant.com'
syncDatabase = 'u391630018'
syncUser = 'apikey-8d34200f26004b4c9646929853fdd852'
syncPassword = '92c8dbd20b1dcf2ee28c2a99508bce0d2c6446d7'

couch = couchdb.Server('https://512940bf-6e0c-4d7b-884b-9fc66185836b-bluemix.cloudant.com')
couch.resource.credentials = (syncUser, syncPassword)
serverDB = couch[syncDatabase]

all_tasks_df = pd.DataFrame()

def get_parent_list(task, categories):

    parent = [item for item in categories if item['_id'] == task['parentId']][0]
    parent_list = [parent]

    while parent['parentId'] != 'root':
        parent = [item for item in categories if item['_id'] == parent['parentId']][0]
        parent_list.append(parent)

    return parent_list


def parse_task(task, categories):
    
    parent_list = get_parent_list(task, categories)
    
    parent_sequence = '/'.join([o['title'] for o in parent_list])
    
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

start = time.time()
categories = list(serverDB.find({'selector': {'db': 'Categories'}}))
all_tasks = serverDB.find({'selector': {'db': 'Tasks'}})

task_df_list = map(parse_task, all_tasks, repeat(categories))

task_df = pd.concat(task_df_list)
task_df.to_csv('./temp_cache/marvin_tasks.csv', index=False)
end = time.time()

print (end - start)

print ('foo')