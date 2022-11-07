import os
from unicodedata import name
import pandas as pd
import mintapi
import json

from typing import List
from webdriver_manager.firefox import GeckoDriverManager
from seleniumrequests import Firefox


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

        return Mint_API_Getter.process_mint_df(accounts, ret_cols)

    def get_transactions_df(mint_conn):

        transactions = mint_conn.get_transaction_data(limit=1000000)

        ret_cols = ["date", "description", "amount", "type", "category", "accountId"]

        return Mint_API_Getter.process_mint_df(transactions, ret_cols)

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
        return Mint_API_Getter.process_mint_df(investments, ret_cols)

    def get_budgets_df(mint_conn):

        budgets = mint_conn.get_budget_data()

        ret_cols = ["budgetDate" "name", "amount", "budgetAmount"]
        budgets_df = Mint_API_Getter.process_mint_df(budgets, ret_cols)

        budgets_df = pd.concat(
            [
                budgets_df.drop(columns={"category"}),
                budgets_df["category"].apply(pd.Series),
            ],
            axis=1,
        )
