#curl.exe -X  POST "http://127.0.0.1:8000/get_historical_data?user_name=jjm&read_cache=true&write_cache=true"

import os
import pandas as pd
import requests

method = 'get_historical_data'
api_server_url = 'http://127.0.0.1:8000/'

url = api_server_url + method
response = requests.post(url, verify=False)

ret_df = pd.DataFrame(response.json())