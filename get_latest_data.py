import os
from data_getters.get_exist_data import Exist_Processor
from data_getters.get_manual_files import Manual_Processor
from data_getters.get_marvin_data import Marvin_Processor
from data_getters.get_mint_data import Mint_API_Getter, Mint_Processor
from data_getters.utils import Data_Getter_Utils

CALL_MINT = False

if __name__ == "__main__":
    user_name = "jjm"
    data_getter = Data_Getter_Utils()
    user_config = data_getter.get_user_config(user_name)

    existing_cache = data_getter.get_existing_cache()

    for user, creds in user_config["mint_login"].items():
        if user == "dmg":
            continue

        if CALL_MINT:
            mint_conn = Mint_API_Getter.get_mint_conn(creds)

            investments_df = Mint_API_Getter.get_investments_df(mint_conn, user)
            accounts_df = Mint_API_Getter.get_accounts_df(mint_conn, user)

            transactions_df = Mint_API_Getter.get_transactions_df(mint_conn, user)
            budgets_df = Mint_API_Getter.get_budgets_df(mint_conn, user)

        if user == "jjm":
            Manual_Processor.get_sleep_df_from_xml(user_config)

            Marvin_Processor.get_marvin_habit_data(user_config)
            Marvin_Processor.get_marvin_task_data(user_config)
            Exist_Processor.get_exist_data(user_config)

        Mint_Processor.clean_budgets(user_config, user)
        Mint_Processor.clean_accounts(user_config, user)
        Mint_Processor.clean_transactions(user_config, user)

    new_cache = data_getter.get_existing_cache()

    if len(new_cache) == len(existing_cache) * 2:
        [os.remove(x) for x in existing_cache]
