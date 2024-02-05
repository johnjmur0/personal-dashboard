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

    async def get_monarch_transactions_df(self, monarch_conn) -> pd.DataFrame:

        raw_transactions = await self.get_monarch_transactions(monarch_conn)

        key_cols = [
            "date",
            "category",
            "account",
            "tags",
            "amount",
        ]

        raw_df = pd.DataFrame.from_dict(raw_transactions["allTransactions"]["results"])[
            key_cols
        ]

        select_key_map = {
            "account": "displayName",
            "category": "name",
            "tags": "name",
        }

        clean_df = raw_df[["date", "amount"]]

        clean_df["account"] = pd.json_normalize(raw_df["account"])[
            select_key_map["account"]
        ]
        clean_df["category"] = pd.json_normalize(raw_df["category"])[
            select_key_map["category"]
        ]

        clean_df["tags"] = pd.json_normalize(raw_df.explode("tags")["tags"])[
            select_key_map["tags"]
        ]

        clean_df["date"] = pd.to_datetime(clean_df["date"])

        return clean_df

    @staticmethod
    async def get_monarch_budgets(monarch_conn: MonarchMoney) -> pd.DataFrame:

        transactions = await monarch_conn.get_budgets()
        return transactions


class Monarch_Processor:

    @staticmethod
    def process_monarch_transactions(transactions_dict: dict) -> pd.DataFrame:

        pass
