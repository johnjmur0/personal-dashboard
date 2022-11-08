import os
import sys
import time
import subprocess
from data_getters.get_exist_data import Exist_Dashboard_Helpers, Exist_Processor

# from data_getters.utils import get_latest_file, get_user_config
from data_getters.get_finances import Finances_Processor
from data_getters.get_manual_files import Manual_Processor
from data_getters.get_marvin_data import Marvin_Processor
from data_getters.get_mint_data import Mint_API_Getter
from data_getters.utils import Data_Getter_Utils

CALL_MINT = True

if __name__ == "__main__":

    user_name = "jjm"  # sys.argv[1]
    user_config = Data_Getter_Utils.get_user_config(user_name)

    if CALL_MINT:

        mint_conn = Mint_API_Getter.get_mint_conn(user_config)

        transactions_df = Mint_API_Getter.get_transactions_df(mint_conn)
        budgets_df = Mint_API_Getter.get_budgets_df(mint_conn)

        investments_df = Mint_API_Getter.get_investments_df(mint_conn)
        accounts_df = Mint_API_Getter.get_accounts_df(mint_conn)

    Manual_Processor.get_sleep_df(user_config)

    Marvin_Processor.get_marvin_checkin_data(user_config)
    Marvin_Processor.get_latest_data(user_config)
    Exist_Processor.get_latest_data(user_config)
