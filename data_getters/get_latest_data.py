import sys

# from data_getters.utils import get_latest_file, get_user_config
from get_finances import Finances_Processor
from get_exist_data import Exist_Processor
from get_marvin_data import Marvin_Processor

if __name__ == "__main__":

    user_name = "jjm"  # sys.argv[1]

    Finances_Processor.get_mint_historical_data(user_name, read_cache=False)

    Exist_Processor.get_latest_data(user_name)
    Marvin_Processor.get_latest_data(user_name)

    Finances_Processor.get_current_accounts(user_name)