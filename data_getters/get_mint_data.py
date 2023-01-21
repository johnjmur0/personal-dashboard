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

    def get_accounts_df(mint_conn, user_name: str):

        accounts = mint_conn.get_account_data()

        ret_cols = [
            "name",
            "type",
            "systemStatus",
            "currentBalance",
            "availableBalance",
        ]

        accounts_df = Mint_API_Getter.process_mint_df(accounts, ret_cols)

        Data_Getter_Utils.write_temp_cache(
            accounts_df, f"mint_accounts_raw_{user_name}"
        )

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
            # TODO not always there in all datasets, why?
            # "symbol",
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
    def category_dict_to_df(category_dict: dict):

        category_df = pd.melt(
            pd.DataFrame(dict([(k, pd.Series(v)) for k, v in category_dict.items()]))
        )

        category_df.rename(
            columns={"variable": "category", "value": "name"},
            inplace=True,
        )

        category_df = category_df[~pd.isnull(category_df["name"])]

        return category_df

    def get_category_df(user_config: dict):

        agg_categories_df = Mint_Processor.category_dict_to_df(
            user_config["aggregate_categories"]
        )
        meta_categories_df = Mint_Processor.category_dict_to_df(
            user_config["meta_categories"]
        )

        return meta_categories_df.rename(
            columns={"category": "meta_category", "name": "category"}
        ).merge(agg_categories_df, on="category")

    def clean_budgets(user_config: dict, user_name: str):

        raw_budgets_df = Data_Getter_Utils().get_latest_file(
            f"mint_budgets_raw_{user_name}"
        )

        raw_budgets_df["budgetDate"] = pd.to_datetime(raw_budgets_df["budgetDate"])
        raw_budgets_df = raw_budgets_df[
            raw_budgets_df["budgetDate"] == max(raw_budgets_df["budgetDate"])
        ]

        category_df = Mint_Processor.get_category_df(user_config)

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

    def clean_transactions(user_config: dict, user_name: str):

        raw_transactions_df = Data_Getter_Utils().get_latest_file(
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

        category_df = Mint_Processor.get_category_df(user_config)

        agg_transactions_df = (
            raw_transactions_df.merge(category_df, on="name")
            .groupby(["year", "month", "day", "category"], as_index=False)
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

    def clean_accounts(user_config: dict, user_name: str):

        raw_accounts_df = Data_Getter_Utils().get_latest_file(
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

        clean_accounts_df.rename(columns={"currentBalance": "total"}, inplace=True)

        Data_Getter_Utils.write_temp_cache(
            clean_accounts_df, f"account_totals_{user_name}"
        )

        return clean_accounts_df


class Finances_Dashboard_Helpers:

    def get_month_sum_df(
        finance_df: pd.DataFrame, remove_category_list=["bonus", "investment"]
    ):

        regular_finances = finance_df[
            ~finance_df["category"].isin(remove_category_list)
        ]
        month_sum_df = (
            regular_finances.groupby(["year", "month"])
            .agg({"total": "sum"})
            .reset_index(drop=False)
        )

        month_sum_df["day"] = 1
        month_sum_df["datetime"] = pd.to_datetime(
            month_sum_df[["year", "month", "day"]]
        )

        return month_sum_df

    def create_spend_budget_df(
        finance_df: pd.DataFrame,
        budget_df: pd.DataFrame,
        year: int,
        month: int,
        housing_payment: int = 0,
        profit_target: int = 3000,
    ):

        filter_df = (
            finance_df[(finance_df["year"] == year) & (finance_df["month"] == month)]
            .groupby("category")
            .agg({"total": "sum"})
            .reset_index(drop=False)
        )

        filter_df = filter_df.merge(budget_df, how="left", on="category")
        filter_df["budget"] = np.where(
            np.isnan(filter_df["budget"]), 0, filter_df["budget"]
        )

        filter_df[["year", "month"]] = [year, month]

        filter_df = pd.concat(
            [
                filter_df,
                pd.DataFrame(
                    data={
                        "year": [year],
                        "month": [month],
                        "category": "profit/loss",
                        "budget": [profit_target],
                        "total": [filter_df["total"].sum()],
                    }
                ),
            ]
        )

        filter_df = filter_df[
            (abs(filter_df["total"]) > 100) & (filter_df["category"] != "paycheck")
        ]

        return pd.melt(
            filter_df,
            id_vars=["category", "year", "month"],
            value_vars=["total", "budget"],
        )

    def get_monthly_income(finance_df: pd.DataFrame, month: int, year: int):

        return finance_df[
            (finance_df["month"] == month)
            & (finance_df["year"] == year)
            & (finance_df["category"] == "income")
        ]["total"].sum()

    def get_budget_shortfall(
        finance_df: pd.DataFrame,
        profit_target: int,
        month: int,
        year: int,
        historical_start_year: int,
    ):

        monthly_income = Finances_Dashboard_Helpers.get_monthly_income(
            finance_df, month, year
        )

        avg_spend = (
            finance_df[
                (finance_df["year"] >= historical_start_year)
                & ~(finance_df["category"].isin(["income", "bonus"]))
            ]
            .groupby(["year", "month"])
            .agg({"total": "sum"})
            .reset_index(drop=False)["total"]
            .mean()
        )

        return (avg_spend + monthly_income) - profit_target
