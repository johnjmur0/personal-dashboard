import pandas as pd
from utils import get_user_config

# Temp holdover for sleep data until I get a replacement for exist
class Manual_Processor:
    def get_sleep_df(user_name: dict):

        user_config = get_user_config(user_name)

        file_path = user_config["manual_files"]["sleep_xlsx_path"]
        week_df = pd.read_excel(open(file_path, "rb"), sheet_name="weekly_average")

        return week_df
