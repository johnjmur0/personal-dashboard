import sys

from data_getters.get_exist_data import Exist_Processor
from data_getters.get_manual_files import Manual_Processor
from data_getters.get_marvin_data import Marvin_Processor
from data_getters.get_mint_data import Mint_API_Getter, Mint_Processor
from data_getters.utils import Data_Getter_Utils

CALL_MINT = True

if __name__ == "__main__":

    user_name = sys.argv[1]
    user_config = Data_Getter_Utils.get_user_config(user_name)

    if CALL_MINT:

        for user, creds in user_config["mint_login"].items():

            mint_conn = Mint_API_Getter.get_mint_conn(creds)

            investments_df = Mint_API_Getter.get_investments_df(mint_conn, user)
            accounts_df = Mint_API_Getter.get_accounts_df(mint_conn, user)

            transactions_df = Mint_API_Getter.get_transactions_df(mint_conn, user)
            budgets_df = Mint_API_Getter.get_budgets_df(mint_conn, user)

    for user, creds in user_config["mint_login"].items():

        Mint_Processor.clean_budgets(user_config, user)
        Mint_Processor.clean_accounts(user_config, user)
        Mint_Processor.clean_transactions(user_config, user)

        if user == "jjm":
            Manual_Processor.get_sleep_df(user_config)

            Marvin_Processor.get_marvin_habit_data(user_config)
            Marvin_Processor.get_marvin_task_data(user_config)
            Exist_Processor.get_exist_data(user_config)
