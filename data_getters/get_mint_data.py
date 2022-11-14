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
    def get_mint_conn(login_config: dict):

        driver = Firefox(executable_path=GeckoDriverManager().install())

        return mintapi.Mint(
            email=login_config["login_email"],
            password=login_config["password"],
            mfa_method="soft-token",
            mfa_token=login_config["mfa_token"],
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

    def get_transactions_df(mint_conn, user_name: str):

        transactions = mint_conn.get_transaction_data(limit=1000000)

        ret_cols = ["date", "description", "amount", "type", "category", "accountId"]

        transactions_df = Mint_API_Getter.process_mint_df(transactions, ret_cols)

        transactions_df = Mint_API_Getter.expand_category_col(
            transactions_df, ret_cols, ["name", "parentName"]
        )

        Data_Getter_Utils.write_temp_cache(
            transactions_df, f"mint_transactions_raw_{user_name}"
        )

        return transactions_df

    def get_investments_df(mint_conn, user_name: str):

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

        Data_Getter_Utils.write_temp_cache(
            investments_df, f"mint_investments_raw_{user_name}"
        )

        return investments_df

    def get_budgets_df(mint_conn, user_name: str):

        budgets = mint_conn.get_budget_data()

        ret_cols = ["budgetDate", "category", "amount", "budgetAmount"]
        budgets_df = Mint_API_Getter.process_mint_df(budgets, ret_cols)

        budgets_df = Mint_API_Getter.expand_category_col(budgets_df, ret_cols, ["name"])

        Data_Getter_Utils.write_temp_cache(budgets_df, f"mint_budgets_raw_{user_name}")

        return budgets_df


class Mint_Processor:
    def clean_transactions(user_config: dict, user_name: str):

        raw_transactions_df = Data_Getter_Utils.get_latest_file(
            f"mint_transactions_raw_{user_name}"
        )

        raw_transactions_df["parentName"] = np.where(
            raw_transactions_df["parentName"] == "Root",
            raw_transactions_df["name"],
            raw_transactions_df["parentName"],
        )

        raw_transactions_df["date"] = pd.to_datetime(raw_transactions_df["date"])

        raw_transactions_df["year"] = raw_transactions_df["date"].dt.year
        raw_transactions_df["month"] = raw_transactions_df["date"].dt.month
        raw_transactions_df["day"] = raw_transactions_df["date"].dt.day

        def category_dict_to_df(category_dict: dict):

            category_df = pd.melt(
                pd.DataFrame(
                    dict([(k, pd.Series(v)) for k, v in category_dict.items()])
                )
            )

            category_df.rename(
                columns={"variable": "category", "value": "name"},
                inplace=True,
            )

            category_df = category_df[~pd.isnull(category_df["name"])]

            return category_df

        agg_categories_df = category_dict_to_df(user_config["aggregate_categories"])
        meta_categories_df = category_dict_to_df(user_config["meta_categories"])

        agg_transactions_df = (
            raw_transactions_df.merge(
                meta_categories_df.rename(
                    columns={"category": "meta_category", "name": "category"}
                ).merge(agg_categories_df, on="category"),
                on="name",
            )
            .groupby(["year", "month", "day", "meta_category"], as_index=False)
            .agg({"amount": "sum"})
        )

        agg_transactions_df["timestamp"] = pd.to_datetime(
            agg_transactions_df[["year", "month", "day"]]
        )

        agg_transactions_df.rename(
            columns={"meta_category": "category", "amount": "total"}, inplace=True
        )

        Data_Getter_Utils.write_temp_cache(
            agg_transactions_df, f"daily_finances_{user_name}"
        )
        return agg_transactions_df

    def clean_accounts(user_config: dict, user_name: str):

        raw_accounts_df = Data_Getter_Utils.get_latest_file(
            f"mint_accounts_raw_{user_name}"
        )

        conditions = [
            raw_accounts_df["type"].isin(
                ["CreditAccount", "BankAccount", "CashAccount"]
            ),
            raw_accounts_df["type"].isin(["InvestmentAccount"]),
            raw_accounts_df["type"].isin(["LoanAccount"]),
        ]
        choices = ["bank", "investment", "loan"]

        raw_accounts_df["account_type"] = np.select(conditions, choices, default=np.nan)

        clean_accounts_df = (
            raw_accounts_df[raw_accounts_df["systemStatus"] == "ACTIVE"]
            .groupby("account_type", as_index=False)
            .agg({"currentBalance": "sum"})
        )

        clean_accounts_df.rename(
            columns={"currentBalance": "total"}, inplace=True
        )

        Data_Getter_Utils.write_temp_cache(
            clean_accounts_df, f"account_totals_{user_name}"
        )

        return clean_accounts_df
