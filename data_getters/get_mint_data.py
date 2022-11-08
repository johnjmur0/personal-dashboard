import os
from unicodedata import name
import pandas as pd
import numpy as np
import mintapi
import json

from typing import List
from webdriver_manager.firefox import GeckoDriverManager
from seleniumrequests import Firefox

from data_getters.utils import Data_Getter_Utils


class Mint_API_Getter:

    # https://github.com/mintapi/mintapi
    def get_mint_conn(user_config: dict):

        driver = Firefox(executable_path=GeckoDriverManager().install())

        return mintapi.Mint(
            email=user_config["mint_login"]["login_email"],
            password=user_config["mint_login"]["password"],
            mfa_method="soft-token",
            mfa_token=user_config["mint_login"]["mfa_token"],
            headless=False,
            use_chromedriver_on_path=False,
            wait_for_sync_timeout=300,
            driver=driver,
        )

    def process_mint_df(mint_json_return: json, ret_cols: List[str]) -> pd.DataFrame:

        ret_df = pd.DataFrame()

        for entry in mint_json_return:
            ret_df = pd.concat(
                [ret_df, pd.DataFrame.from_dict(entry, orient="index").T]
            )

        ret_df = ret_df[ret_cols].reset_index(drop=True)

        return ret_df

    def expand_category_col(df, ret_cols, keep_names):

        df = pd.concat(
            [
                df.drop(columns={"category"}),
                df["category"].apply(pd.Series),
            ],
            axis=1,
        )

        ret_cols = set(ret_cols) - set(["category"])
        ret_cols = list(ret_cols) + keep_names

        return df[ret_cols]

    def close_mint_conn(mint_conn):
        mint_conn.close()

    def get_accounts_df(mint_conn):

        accounts = mint_conn.get_account_data()

        ret_cols = [
            "name",
            "type",
            "systemStatus",
            "currentBalance",
            "availableBalance",
        ]

        accounts_df = Mint_API_Getter.process_mint_df(accounts, ret_cols)

        Data_Getter_Utils.write_temp_cache(accounts_df, "mint_accounts_raw")

        return accounts_df

    def get_transactions_df(mint_conn):

        transactions = mint_conn.get_transaction_data(limit=1000000)

        ret_cols = ["date", "description", "amount", "type", "category", "accountId"]

        transactions_df = Mint_API_Getter.process_mint_df(transactions, ret_cols)

        transactions_df = Mint_API_Getter.expand_category_col(
            transactions_df, ret_cols, ["name", "parentName"]
        )

        Data_Getter_Utils.write_temp_cache(transactions_df, "mint_transactions_raw")

        return transactions_df

    def get_investments_df(mint_conn):

        investments = mint_conn.get_investment_data()

        ret_cols = [
            "symbol",
            "description",
            "initialTotalCost",
            "currentValue",
            "averagePricePaid",
            "currentPrice",
        ]

        investments_df = Mint_API_Getter.process_mint_df(investments, ret_cols)

        Data_Getter_Utils.write_temp_cache(investments_df, "mint_investments_raw")

        return investments_df

    def get_budgets_df(mint_conn):

        budgets = mint_conn.get_budget_data()

        ret_cols = ["budgetDate", "category", "amount", "budgetAmount"]
        budgets_df = Mint_API_Getter.process_mint_df(budgets, ret_cols)

        budgets_df = Mint_API_Getter.expand_category_col(budgets_df, ret_cols, ["name"])

        Data_Getter_Utils.write_temp_cache(budgets_df, "mint_budgets_raw")

        return budgets_df


class Mint_Processor:
    def clean_transactions(user_config: dict):

        raw_transactions_df = Data_Getter_Utils.get_latest_file("mint_transactions_raw")

        raw_transactions_df["parentName"] = np.where(
            raw_transactions_df["parentName"] == "Root",
            raw_transactions_df["name"],
            raw_transactions_df["parentName"],
        )

        agg_categories_df = pd.melt(
            pd.DataFrame(
                dict(
                    [
                        (k, pd.Series(v))
                        for k, v in user_config["aggregate_categories"].items()
                    ]
                )
            )
        )

        agg_categories_df.rename(
            columns={"variable": "category", "value": "name"}, inplace=True
        )

        raw_transactions_df["date"] = pd.to_datetime(raw_transactions_df["date"])

        raw_transactions_df["year"] = raw_transactions_df["date"].dt.year
        raw_transactions_df["month"] = raw_transactions_df["date"].dt.month

        agg_transactions_df = (
            raw_transactions_df.merge(
                agg_categories_df[~pd.isnull(agg_categories_df["name"])], on="name"
            )
            .groupby(["year", "month", "category"], as_index=False)
            .agg({"amount": "sum"})
        )

        return agg_transactions_df
