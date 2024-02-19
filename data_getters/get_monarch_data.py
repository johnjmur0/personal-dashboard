import os
import numpy as np
import math
import pandas as pd
from monarchmoney import MonarchMoney
from data_getters.utils import Data_Getter_Utils


class Monarch_API_Getter:

    @staticmethod
    async def get_monarch_conn(login_config: dict):

        mm = MonarchMoney(timeout=180)

        await mm.login(
            email=login_config["login_email"],
            password=login_config["password"],
        )

        return mm

    async def get_monarch_accounts(self, monarch_conn: MonarchMoney) -> pd.DataFrame:

        accounts = await monarch_conn.get_accounts()
        return accounts

    async def get_monarch_accounts_df(
        self, monarch_conn: MonarchMoney, user_name: str
    ) -> pd.DataFrame:

        raw_accounts = await self.get_monarch_accounts(monarch_conn)

        accounts_df = pd.DataFrame.from_dict(raw_accounts["accounts"])

        selet_cols = ["id", "displayName", "currentBalance", "type"]
        accounts_df = accounts_df[selet_cols]

        accounts_df["type"] = pd.json_normalize(accounts_df["type"])["display"]

        accounts_df["type"] = np.where(
            accounts_df["type"] == "Credit Cards", "Cash", accounts_df["type"]
        )

        accounts_df["type"] = accounts_df["type"].str.lower()

        Data_Getter_Utils.write_temp_cache(
            accounts_df, f"monarch_accounts_raw_{user_name}"
        )

        return accounts_df

    async def get_monarch_transactions(
        self,
        monarch_conn: MonarchMoney,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        limit: int,
    ) -> pd.DataFrame:

        transactions = await monarch_conn.get_transactions(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            limit=limit,
        )
        return transactions

    async def get_monarch_transactions_df(
        self,
        monarch_conn: MonarchMoney,
        user_name: str,
        limit: int = 1000,
    ) -> pd.DataFrame:

        today = pd.Timestamp.now()

        cached_transactions_df = Data_Getter_Utils().get_latest_file(
            f"monarch_transactions_cached_{user_name}"
        )

        cached_transactions_df["date"] = pd.to_datetime(cached_transactions_df["date"])
        start_date = cached_transactions_df["date"].max()

        new_transactions = await self.get_monarch_transactions(
            monarch_conn, start_date=start_date, end_date=today, limit=limit
        )

        if len(new_transactions) == 0:
            return cached_transactions_df

        key_cols = [
            "date",
            "category",
            "account",
            "tags",
            "amount",
        ]

        raw_df = pd.DataFrame.from_dict(new_transactions["allTransactions"]["results"])[
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

        new_cache_df = (
            pd.concat([clean_df, cached_transactions_df])
            .reset_index(drop=True)
            .drop_duplicates()
        )

        Data_Getter_Utils.write_temp_cache(
            new_cache_df, f"monarch_transactions_cached_{user_name}"
        )

        return clean_df

    async def _backfill_monarch_transactions(
        self,
        monarch_conn: MonarchMoney,
        user_name: str,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        limit: int = 1000,
    ):

        earliest_end_date = end_date

        all_transaction_list = []
        while earliest_end_date > start_date:

            ret_df = await self.get_monarch_transactions_df(
                monarch_conn=monarch_conn,
                user_name=user_name,
                start_date=start_date,
                end_date=earliest_end_date,
                limit=limit,
            )

            all_transaction_list.append(ret_df)

            earliest_end_date = ret_df["date"].min()

        data_getter = Data_Getter_Utils()

        all_transaction_df = pd.concat(all_transaction_list).drop_duplicates()

        data_getter.write_temp_cache(
            all_transaction_df, f"monarch_transactions_cached_{user_name}"
        )

        duped_cache = data_getter.get_existing_cache()

        os.remove([x for x in duped_cache if "monarch_transactions_raw" in x])

    async def get_monarch_budgets(self, monarch_conn: MonarchMoney) -> pd.DataFrame:

        budgets = await monarch_conn.get_budgets()
        return budgets

    async def get_monarch_budgets_df(
        self, monarch_conn: MonarchMoney, user_name: str
    ) -> pd.DataFrame:

        raw_budgets = await self.get_monarch_budgets(monarch_conn)

        amount_df = pd.DataFrame.from_dict(
            raw_budgets["budgetData"]["monthlyAmountsByCategory"]
        )

        labeled_amount_df = pd.concat(
            [
                pd.json_normalize(amount_df["category"]),
                pd.json_normalize(pd.json_normalize(amount_df["monthlyAmounts"])[0])[
                    "plannedCashFlowAmount"
                ],
            ],
            axis=1,
        ).rename(columns={"plannedCashFlowAmount": "budgetAmount"})[
            ["id", "budgetAmount"]
        ]

        raw_category_df = pd.DataFrame.from_dict(raw_budgets["categoryGroups"])

        meta_categories_df = raw_category_df.explode("categories")[
            ["id", "name", "type"]
        ]

        sub_category_df = pd.json_normalize(
            raw_category_df.explode("categories")["categories"]
        )[["id", "name"]]

        joined_category_df = pd.concat(
            [
                meta_categories_df.rename(
                    columns={"id": "meta_id", "name": "meta_name"}
                ).reset_index(drop=True),
                sub_category_df,
            ],
            axis=1,
        )

        all_joined_df = joined_category_df.merge(
            labeled_amount_df, on="id", how="left"
        ).dropna()

        Data_Getter_Utils.write_temp_cache(
            all_joined_df, f"monarch_budgets_raw_{user_name}"
        )

        return all_joined_df


class Monarch_Processor:

    @staticmethod
    def clean_transactions(user_config: dict, user_name: str) -> pd.DataFrame:

        raw_transactions_df = Data_Getter_Utils().get_latest_file(
            f"monarch_transactions_cached_{user_name}"
        )

        raw_transactions_df["date"] = pd.to_datetime(raw_transactions_df["date"])

        raw_transactions_df["year"] = raw_transactions_df["date"].dt.year
        raw_transactions_df["month"] = raw_transactions_df["date"].dt.month
        raw_transactions_df["day"] = raw_transactions_df["date"].dt.day

        category_df = Data_Getter_Utils.get_budget_category_df(user_config)

        agg_transactions_df = (
            raw_transactions_df.rename(columns={"category": "name"})
            .merge(category_df, on="name")
            .groupby(["year", "month", "day", "category", "tags"], as_index=False)
            .agg({"amount": "sum"})
        )

        agg_transactions_df["timestamp"] = pd.to_datetime(
            agg_transactions_df[["year", "month", "day"]]
        )

        agg_transactions_df.rename(columns={"amount": "total"}, inplace=True)

        Data_Getter_Utils.write_temp_cache(
            agg_transactions_df, f"daily_finances_{user_name}"
        )
        return agg_transactions_df

    @staticmethod
    def clean_budgets(user_config: dict, user_name: str) -> pd.DataFrame:

        raw_budgets_df = (
            Data_Getter_Utils()
            .get_latest_file(f"monarch_budgets_raw_{user_name}")
            .drop_duplicates()
        )

        category_df = Data_Getter_Utils.get_budget_category_df(user_config)

        agg_budgets_df = (
            raw_budgets_df.merge(category_df, on="name")
            .groupby(["category"], as_index=False)
            .agg({"budgetAmount": "sum"})
        )

        agg_budgets_df = agg_budgets_df.rename(columns={"budgetAmount": "budget"})
        agg_budgets_df["budget"] = np.where(
            agg_budgets_df["category"] != "paycheck",
            agg_budgets_df["budget"] * -1,
            agg_budgets_df["budget"],
        )

        Data_Getter_Utils.write_temp_cache(
            agg_budgets_df, f"monthly_budget_{user_name}"
        )

        return agg_budgets_df

    @staticmethod
    def clean_accounts(user_config: dict, user_name: str) -> pd.DataFrame:

        raw_accounts_df = Data_Getter_Utils().get_latest_file(
            f"monarch_accounts_raw_{user_name}"
        )

        active_accounts_df = raw_accounts_df[raw_accounts_df["currentBalance"] != 0]

        active_accounts_df["tags"] = active_accounts_df["displayName"].str.split(
            " ", expand=True
        )[0]

        agg_accounts_df = (
            active_accounts_df.groupby(["tags", "type"], as_index=False)
            .agg({"currentBalance": "sum"})
            .rename(columns={"type": "account_type", "currentBalance": "total"})
        )

        Data_Getter_Utils.write_temp_cache(
            agg_accounts_df, f"account_totals_{user_name}"
        )

        return agg_accounts_df