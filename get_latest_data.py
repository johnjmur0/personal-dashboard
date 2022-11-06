import os
import sys
import subprocess
from data_getters.get_exist_data import Exist_Dashboard_Helpers, Exist_Processor

# from data_getters.utils import get_latest_file, get_user_config
from data_getters.get_finances import Finances_Processor
from data_getters.get_manual_files import Manual_Processor
from data_getters.get_marvin_data import Marvin_Processor
from data_getters.utils import get_user_config

CALL_MINT = True

if __name__ == "__main__":

    user_name = "jjm"  # sys.argv[1]
    user_config = get_user_config(user_name)

    # TODO replace all these w/ config instead of user_name
    Manual_Processor.get_sleep_df(user_config)

    Exist_Processor.get_latest_data(user_name)

    Marvin_Processor.get_latest_data(user_name)

    if CALL_MINT:

        dir = os.getcwd()
        api_launcer = "./data_getters/start_finance_api.ps1"

        p = subprocess.Popen(
            ["powershell.exe", os.path.join(dir, api_launcer)], stdout=sys.stdout
        )

        Finances_Processor.get_current_accounts(user_name)
        Finances_Processor.get_mint_historical_data(user_name)

    Marvin_Processor.get_marvin_checkin_data(user_name)
