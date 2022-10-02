import sys

# from data_getters.utils import get_latest_file, get_user_config
from get_finances import Finances_Processor
from get_exist_data import Exist_Processor, Exist_Dashboard_Helpers
from get_marvin_data import Marvin_Processor
from utils import get_latest_file, get_user_config

if __name__ == "__main__":

    user_name = "jjm"  # sys.argv[1]

    Exist_Processor.get_latest_data(user_name)

    habit_df = Exist_Dashboard_Helpers.format_exist_df(
        get_latest_file(file_prefix="exist_data"), get_user_config("jjm")
    )

    Marvin_Processor.get_marvin_checkin_data(user_name)

    Finances_Processor.get_mint_historical_data(user_name, read_cache=True)
    Marvin_Processor.get_latest_data(user_name)

    Finances_Processor.get_current_accounts(user_name)
