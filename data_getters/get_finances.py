# curl.exe -X  POST "http://127.0.0.1:8000/get_historical_data?user_name=jjm&read_cache=true&write_cache=true"

import os
import datetime
import pandas as pd
import requests


class Finances_Processor:
    def send_finance_request_generic(
        method: str, user_name: str, read_cache: bool = False
    ):

        api_server_url = "http://127.0.0.1:8000/"

        url = (
            api_server_url
            + method
            + f"?user_name={user_name}&read_cache={read_cache}&write_cache=False"
        )
        response = requests.post(url, verify=False)

        if response.status_code == 500:
            # TODO figure out why this always fails the first time
            if "rpytools" in response.text:
                response = requests.post(url, verify=False)

        ret_df = pd.DataFrame(response.json())

        return ret_df

    def get_mint_historical_data(user_name: str, read_cache: bool = True):

        method = "get_historical_by_category"

        ret_df = Finances_Processor.send_finance_request_generic(
            method, user_name, read_cache
        )
        ret_df["timestamp"] = pd.to_datetime(ret_df[["year", "month", "day"]])

        date_str = ret_df["timestamp"].max().date()
        ret_df.to_csv(f"./temp_cache/daily_finances_{date_str}.csv")
        return ret_df

    def get_current_accounts(user_name: str):

        method = "get_current_accounts"
        ret_df = Finances_Processor.send_finance_request_generic(
            method, user_name, read_cache=True
        )

        ret_df.rename(
            columns={"accountType": "account_type", "Total": "total"}, inplace=True
        )
        date_str = datetime.datetime.now().date()
        ret_df.to_csv(f"./temp_cache/account_totals_{date_str}.csv")

        return ret_df


class Finances_Dashboard_Helpers:

    # TODO Ideally I can get budget values from Mint
    def get_general_budget(user_config: dict):

        budget_df = (
            pd.DataFrame(
                data=user_config["finances_config"]["general_budget"], index=[0]
            )
            .T.reset_index(drop=False)
            .rename(columns={"index": "category", 0: "budget"})
        )

        return budget_df

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

        if housing_payment != 0:
            # TODO handle bills with housing for real, not multiplier
            budget_df.loc[budget_df["category"] == "housing", "budget"] = (
                housing_payment * 1.05
            )

            current_housing_payment = filter_df[filter_df["category"] == "housing"][
                "total"
            ].sum()
            housing_adder = housing_payment - current_housing_payment
        else:
            housing_adder = 0

        filter_df = pd.concat(
            [
                filter_df,
                pd.DataFrame(
                    data={
                        "year": [year],
                        "month": [month],
                        "category": "profit/loss",
                        "budget": [profit_target],
                        "total": [filter_df["total"].sum() + housing_adder],
                    }
                ),
            ]
        )

        filter_df = filter_df[abs(filter_df["total"]) > 100]

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
