import pandas as pd
import os
import asyncio
from data_getters.get_exist_data import Exist_Processor
from data_getters.get_manual_files import Manual_Processor
from data_getters.get_marvin_data import Marvin_Processor
from data_getters.get_mint_data import Mint_API_Getter, Mint_Processor
from data_getters.get_monarch_data import Monarch_API_Getter, Monarch_Processor
from data_getters.utils import Data_Getter_Utils
from typing import Dict


async def get_monarch_data(user: str, creds: Dict[str, str]):
    monarch_helper = Monarch_API_Getter()
    monarch_conn = await monarch_helper.get_monarch_conn(creds)

    await monarch_helper.get_monarch_accounts_df(monarch_conn, user)

    await monarch_helper.get_monarch_transactions_df(monarch_conn, user, limit=1000)
    await monarch_helper.get_monarch_budgets_df(monarch_conn, user)


CALL_MONARCH = False

if __name__ == "__main__":
    user_name = "jjm"
    data_getter = Data_Getter_Utils()
    user_config = data_getter.get_user_config(user_name)

    existing_cache = data_getter.get_existing_cache()

    for user, creds in user_config["mint_login"].items():
        if user == "dmg":
            continue

        if CALL_MONARCH:
            asyncio.run(get_monarch_data(user, creds))
        if user == "jjm":
            # Manual_Processor.get_sleep_df_from_xml(user_config)

            # Marvin_Processor.get_marvin_habit_data(user_config)
            # Marvin_Processor.get_marvin_task_data(user_config)
            # Exist_Processor.get_exist_data(user_config)
            pass

        Monarch_Processor.clean_budgets(user_config, user)
        Monarch_Processor.clean_accounts(user_config, user)
        Monarch_Processor.clean_transactions(user_config, user)

    new_cache = data_getter.get_existing_cache()

    if len(new_cache) == len(existing_cache) * 2:
        [os.remove(x) for x in existing_cache]
