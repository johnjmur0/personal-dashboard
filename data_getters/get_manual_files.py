import xml.etree.ElementTree as ET
import xmltodict
import os
from os import rename
import pandas as pd
import numpy as np
import datetime

# Temp holdover for sleep data until I get a replacement for exist
class Manual_Processor:
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

        sleep_df["start_date"] = sleep_df["sleep_start"].dt.date
        sleep_df["end_date"] = sleep_df["sleep_end"].dt.date

        sleep_df = pd.concat(
            [
                sleep_df.groupby(["start_date"], as_index=False).agg(
                    {"sleep_start": "min"}
                )["sleep_start"],
                sleep_df.groupby(["end_date"], as_index=False).agg(
                    {"sleep_end": "max"}
                )["sleep_end"],
            ]
        )

        sleep_df["year"] = sleep_df["sleep_start"].dt.year
        sleep_df["month"] = sleep_df["sleep_start"].dt.month
        sleep_df["day"] = sleep_df["sleep_start"].dt.day
        sleep_df["week"] = sleep_df["sleep_start"].dt.isocalendar().week

        sleep_df["duration"] = sleep_df["sleep_end"] - sleep_df["sleep_start"]

        sleep_df["bedtime"] = sleep_df["sleep_start"].dt.time
        sleep_df["wakeup"] = sleep_df["sleep_end"].dt.time

        return sleep_df[["year", "month", "week", "bedtime", "wakeup", "duration"]]


class Manual_Dashboard_Helpers:
    def format_sleep_df(
        sleep_df: pd.DataFrame = None, user_config: dict = None
    ) -> pd.DataFrame:

        if sleep_df is None:

            manual_sleep_df = Manual_Processor.get_sleep_df_from_xml(user_config)

            sleep_df = (
                manual_sleep_df.rename(
                    columns={"wakeup": "Wake", "bedtime": "Bed", "duration": "Duration"}
                )
                .melt(
                    id_vars=["year", "month", "week"],
                    value_vars=["Wake", "Bed", "Duration"],
                )
                .rename(
                    columns={
                        "week": "week_number",
                        "variable": "name",
                    }
                )
            )

            duration_subset = sleep_df[sleep_df["name"] == "Duration"]
            duration_subset["value"] = duration_subset["value"].apply(
                lambda x: (datetime.datetime.min + x).time()
            )

            sleep_df = pd.concat(
                [sleep_df[sleep_df["name"] != "Duration"], duration_subset]
            )

        # TODO use marvin targets for this, actual values in alternate way?
        sleep_df["target"] = np.where(
            sleep_df["name"] == "Bedtime",
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
