import requests
import couchdb
import datetime

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

for id in serverDB:
    if serverDB[id]['db'] == 'Tasks':
        task = serverDB[id]
        break

print (task)

name = task['title']
estimate = task['timeEstimate'] / 3600000
project = serverDB[task['parentId']]['title']
category = serverDB[serverDB[task['parentId']]['parentId']]['title']
start_time = datetime.datetime.fromtimestamp(task['times'][1] / 1000)
end_time = datetime.datetime.fromtimestamp(task['times'][1] / 1000)
