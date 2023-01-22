import os
import math
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

from data_getters.utils import Data_Getter_Utils


class Exist_Processor:

    exist_server_url = "https://exist.io/api/2/"
    attributes_endpoint = "attributes/with-values/"

    def get_login_credentials(user_config: dict):

        return {
            "username": user_config["exist_config"]["username"],
            "password": user_config["exist_config"]["password"],
        }

    def get_token_header(login_dict: dict):

        token_endpoint = "auth/simple-token/"

        token_url = Exist_Processor.exist_server_url + token_endpoint
        response = requests.post(token_url, data=login_dict, verify=False)
        token = response.json()["token"]
        token_header = {"Authorization": "Token " + token}
        token_response = requests.get(
            Exist_Processor.exist_server_url + Exist_Processor.attributes_endpoint,
            headers=token_header,
        )

        assert token_response.status_code == 200

        return token_header

    def get_date_range():

        start_date = pd.to_datetime("2021-12-01")
        end_date = datetime.now()

        month_duration = math.ceil((end_date - start_date) / np.timedelta64(1, "M"))
        return pd.date_range(start=start_date, freq="M", periods=month_duration)

    def parse_attribute_response(attributes_response, request_date: pd.Timestamp):

        response_df = pd.DataFrame()
        data = attributes_response.json()

        for attribute in data["results"]:
            label = attribute["label"]
            if len(attribute["values"]) == 0:
                continue
            else:
                attr_df = pd.DataFrame(attribute["values"])
                attr_df["attribute"] = label

            response_df = pd.concat([response_df, attr_df])

        return response_df

    def get_attributes_df(date_range: pd.date_range, login_dict: dict):

        attributes_df = pd.DataFrame()

        token_header = Exist_Processor.get_token_header(login_dict)

        for date in date_range:

            count = date.daysinmonth

            date_params = f"?days={count}&date_max={date.date()}"

            request_str = (
                Exist_Processor.exist_server_url
                + Exist_Processor.attributes_endpoint
                + date_params
            )

            attributes_response = requests.get(request_str, headers=token_header)

            response_df = Exist_Processor.parse_attribute_response(
                attributes_response, date
            )

            while attributes_response.json()["next"] is not None:

                next_page_request = attributes_response.json()["next"]

                attributes_response = requests.get(
                    next_page_request, headers=token_header
                )

                next_page_df = Exist_Processor.parse_attribute_response(
                    attributes_response, date
                )

                response_df = pd.concat([response_df, next_page_df])

            attributes_df = pd.concat([attributes_df, response_df])

        return attributes_df

    def get_page(page):

        response = requests.get(
            url,
            params={"page": page, "limit": 100},
            headers={"Authorization": f"Token {TOKEN}"},
        )

        if response.status_code == 200:
            data = response.json()

            for attribute in data["results"]:
                label = attribute["label"]
                value = attribute["values"][0]["value"]
                attributes[label] = value

            if data["next"] is not None:
                get_page(page + 1)

        else:
            print("Error!", response.content)

    def get_exist_data(user_config: dict):

        login_dict = Exist_Processor.get_login_credentials(user_config)

        exist_df = Exist_Processor.get_attributes_df(
            Exist_Processor.get_date_range(), login_dict
        )

        Data_Getter_Utils.write_temp_cache(exist_df, "exist_data")

class Exist_Dashboard_Helpers:
    def format_exist_df(exist_df: pd.DataFrame, user_config: dict) -> pd.DataFrame:

        key_habits_df = (
            pd.DataFrame(data=user_config["exist_config"]["key_habits"], index=[0])
            .T.reset_index(drop=False)
            .rename(columns={"index": "attribute", 0: "target"})
        )

        exist_df["attribute"] = exist_df["attribute"].str.replace(" ", "_").str.lower()
        exist_df.replace(
            {"attribute": {"bedtime": "sleep_start", "wake_time": "sleep_end"}},
            inplace=True,
        )

        exist_df["value"] = exist_df["value"].fillna(0)

        habit_df = (
            exist_df[exist_df["attribute"].isin(key_habits_df["attribute"])]
            .astype({"value": "float64"})
            .merge(key_habits_df, on="attribute", how="left")
        )

        habit_df["date"] = pd.to_datetime(habit_df["date"])
        habit_df = habit_df[habit_df["date"].dt.date != datetime.now().date()]

        habit_df["year"] = habit_df["date"].dt.year
        habit_df["month"] = habit_df["date"].dt.month

        # region TODO 10/2/22 the sleep data processing wrong b/c of (dumb) limitation on exist's side
        # Using a manual excel sheet I keep for now until I get another solution
        habit_df["value"] = np.where(
            habit_df["attribute"] == "sleep_start",
            ((habit_df["value"] / 60) + 12) % 24,
            habit_df["value"],
        )
        habit_df["value"] = np.where(
            habit_df["attribute"] == "sleep_end",
            habit_df["value"] / 60,
            habit_df["value"],
        )

        habit_df["achieved"] = np.where(
            habit_df["attribute"].isin(["sleep_start", "sleep_end"]),
            habit_df["value"] <= habit_df["target"],
            habit_df["value"] >= habit_df["target"],
        )
        # endregion

        return habit_df

    def get_weekly_rating_df(
        exist_df: pd.DataFrame = None, user_config: dict = None
    ) -> pd.DataFrame:

        if exist_df is None:
            exist_df = Data_Getter_Utils().get_latest_file(file_prefix="exist_data")

        formatted_exist_df = Exist_Dashboard_Helpers.format_exist_df(
                exist_df, user_config
            )

        day_rating = formatted_exist_df[formatted_exist_df["attribute"] == "mood"]

        day_rating["week_number"] = day_rating["date"].dt.isocalendar().week

        day_rating = day_rating.groupby(
            ["year", "month", "week_number"], as_index=False
        ).agg({"value": "mean", "target": "mean"})

        day_rating["name"] = "Rating"
        day_rating["positive"] = True

        return day_rating
