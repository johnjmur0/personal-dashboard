import math
import xml.etree.ElementTree as ET
import xmltodict
import os
import time
from os import rename
import pandas as pd
import numpy as np
import datetime
from data_getters.utils import Data_Getter_Utils


class Manual_Processor:
    # Temp holdover for sleep data until I get a replacement for exist
    def get_sleep_df(user_config: dict) -> pd.DataFrame:
        file_path = user_config["manual_files"]["sleep_xlsx_path"]
        week_df = pd.read_excel(open(file_path, "rb"), sheet_name="weekly_average")

        return week_df

    def get_sleep_df_from_xml(user_config: dict) -> pd.DataFrame:
        file_path = os.path.join(
            user_config["manual_files"]["sleep_xml_path"],
            "export/apple_health_export\export.xml",
        )

        with open(file_path, "r") as xml_file:
            input_data = xmltodict.parse(xml_file.read())

        records_list = input_data["HealthData"]["Record"]
        df = pd.DataFrame(records_list)

        sleep_df = df[df["@type"] == "HKCategoryTypeIdentifierSleepAnalysis"][
            ["@startDate", "@endDate"]
        ]

        sleep_df["sleep_start"] = pd.to_datetime(sleep_df["@startDate"])
        sleep_df["sleep_end"] = pd.to_datetime(sleep_df["@endDate"])

        sleep_df = sleep_df[["sleep_start", "sleep_end"]]

        # Older - start day, hour, min are identical, take max end
        # newer - end day is same, assign value. group by value, take max end, min start
        sleep_df["end_date"] = sleep_df["sleep_end"].dt.date
        sleep_df["wake_obs"] = sleep_df.groupby(["end_date"]).ngroup()

        sleep_df["min_sleep_start"] = (
            sleep_df["sleep_start"].groupby(sleep_df["wake_obs"]).transform("min")
        )
        sleep_df["max_sleep_end"] = (
            sleep_df["sleep_end"].groupby(sleep_df["wake_obs"]).transform("max")
        )

        sleep_df["duration"] = sleep_df["max_sleep_end"] - sleep_df["min_sleep_start"]

        sleep_df = sleep_df[
            ~sleep_df["max_sleep_end"].dt.hour.isin([0, 22, 23, 1, 2, 3])
        ]

        sleep_df = sleep_df[
            ["min_sleep_start", "max_sleep_end", "duration"]
        ].drop_duplicates()

        sleep_df.rename(
            columns={"min_sleep_start": "bedtime", "max_sleep_end": "wakeup"},
            inplace=True,
        )

        sleep_df["year"] = sleep_df["wakeup"].dt.year
        sleep_df["month"] = sleep_df["wakeup"].dt.month
        sleep_df["day"] = sleep_df["wakeup"].dt.day
        sleep_df["week"] = sleep_df["wakeup"].dt.isocalendar().week

        ret_df = sleep_df[["year", "month", "week", "bedtime", "wakeup", "duration"]]

        ret_df.reset_index(drop=False, inplace=True)

        Data_Getter_Utils.write_temp_cache(ret_df, "sleep_data")


class Manual_Dashboard_Helpers:
    def datetime_to_radians(x):
        # radians are calculated using a 24-hour circle, not 12-hour, starting at north and moving clockwise
        time_of_day = x.time()
        seconds_from_midnight = (
            3600 * time_of_day.hour + 60 * time_of_day.minute + time_of_day.second
        )
        radians = float(seconds_from_midnight) / float(24 * 60 * 60) * 2.0 * math.pi
        return radians

    def average_angle(angles):
        # angles measured in radians
        x_sum = np.sum([math.sin(x) for x in angles])
        y_sum = np.sum([math.cos(x) for x in angles])
        x_mean = x_sum / float(len(angles))
        y_mean = y_sum / float(len(angles))
        return np.arctan2(x_mean, y_mean)

    def radians_to_time_of_day(x):
        # radians are measured clockwise from north and represent time in a 24-hour circle
        seconds_from_midnight = int(float(x) / (2.0 * math.pi) * 24.0 * 60.0 * 60.0)
        hour = int((seconds_from_midnight / 3600) % 24)
        minute = (seconds_from_midnight % 3600) // 60
        second = seconds_from_midnight % 60
        return datetime.time(hour, minute, second)

    def average_times_of_day(x):
        # input datetime.datetime array and output datetime.time value
        angles = [Manual_Dashboard_Helpers.datetime_to_radians(y) for y in x]
        avg_angle = Manual_Dashboard_Helpers.average_angle(angles)
        return Manual_Dashboard_Helpers.radians_to_time_of_day(avg_angle)

    def get_avg_sleep_df(sleep_df):
        ret_sleep_df = sleep_df[["name", "target", "positive"]].drop_duplicates()
        avg_sleep_vals = (
            sleep_df[sleep_df["name"] != "Duration"][["name", "value"]]
            .groupby(["name"], as_index=False)
            .apply(
                lambda x: Manual_Dashboard_Helpers.average_times_of_day(
                    x["value"]
                ).strftime("%H:%M")
            )
        )

        ret_sleep_df = ret_sleep_df.merge(
            avg_sleep_vals.rename(columns={None: "value"}), on="name", how="left"
        )

        avg_duration = time.strftime(
            "%H:%M",
            time.gmtime(
                pd.to_timedelta(
                    sleep_df[sleep_df["name"] == "Duration"]["value"].astype(str)
                )
                .dt.total_seconds()
                .mean()
            ),
        )
        ret_sleep_df.loc[ret_sleep_df["name"] == "Duration", "value"] = avg_duration

        return ret_sleep_df

    def format_sleep_df(
        sleep_df: pd.DataFrame = None, user_config: dict = None
    ) -> pd.DataFrame:
        if sleep_df is None:
            sleep_df = Manual_Processor.get_sleep_df_from_xml(user_config)

        sleep_df = sleep_df.rename(
            columns={"wakeup": "Wake", "bedtime": "Bed", "duration": "Duration"}
        ).rename(
            columns={
                "week": "week_number",
            }
        )

        sleep_df["Wake"] = pd.to_datetime(sleep_df["Wake"])
        sleep_df["Bed"] = pd.to_datetime(sleep_df["Bed"])
        sleep_df["Duration"] = pd.to_timedelta(sleep_df["Duration"])

        sleep_df["Duration"] = sleep_df["Duration"].apply(
            lambda x: (datetime.datetime.min + x).time()
        )

        sleep_df = sleep_df.melt(
            id_vars=["year", "month", "week_number"],
            value_vars=["Wake", "Bed", "Duration"],
        ).rename(
            columns={
                "variable": "name",
            }
        )

        # TODO use marvin targets for this, actual values in alternate way?
        sleep_df["target"] = np.where(
            sleep_df["name"] == "Bed",
            datetime.time(22, 0, 0),
            datetime.time(6, 0, 0),
        )

        sleep_df["target"] = np.where(
            sleep_df["name"] == "Duration", datetime.time(8, 30, 0), sleep_df["target"]
        )

        sleep_df["positive"] = np.where(sleep_df["name"] == "Duration", True, False)
        sleep_df["value"] = sleep_df["value"].apply(
            lambda x: x.replace(second=0, microsecond=0)
        )

        return sleep_df
