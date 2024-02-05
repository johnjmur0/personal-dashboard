import math
import pandas as pd
from monarchmoney import MonarchMoney


class Monarch_API_Getter:

    @staticmethod
    async def get_monarch_conn(login_config: dict):

        mm = MonarchMoney()

        await mm.login(
            email=login_config["monarch_config"]["login_email"],
            password=login_config["monarch_config"]["password"],
        )

        return mm

    @staticmethod
    async def get_monarch_accounts(monarch_conn: MonarchMoney) -> pd.DataFrame:

        accounts = await monarch_conn.get_accounts()
        return accounts

    @staticmethod
    async def get_monarch_transactions(monarch_conn: MonarchMoney) -> pd.DataFrame:

        transactions = await monarch_conn.get_transactions(limit=100)
        return transactions

    @staticmethod
    async def get_monarch_budgets(monarch_conn: MonarchMoney) -> pd.DataFrame:

        transactions = await monarch_conn.get_budgets()
        return transactions
