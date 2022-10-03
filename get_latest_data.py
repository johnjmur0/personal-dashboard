import sys

# from data_getters.utils import get_latest_file, get_user_config
from data_getters.get_finances import Finances_Processor
from data_getters.get_exist_data import Exist_Processor, Exist_Dashboard_Helpers
from data_getters.get_marvin_data import Marvin_Processor
from data_getters.get_manual_files import Manual_Processor
from data_getters.utils import get_latest_file, get_user_config

if __name__ == "__main__":

    user_name = "jjm"  # sys.argv[1]

    Marvin_Processor.get_marvin_checkin_data(user_name)
    
    Manual_Processor.get_sleep_df(user_name)

    Exist_Processor.get_latest_data(user_name)

    Finances_Processor.get_mint_historical_data(user_name, read_cache=True)
    Marvin_Processor.get_latest_data(user_name)

    Finances_Processor.get_current_accounts(user_name)
