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


class Manual_Dashboard_Helpers:
    def format_sleep_df(
        sleep_df: pd.DataFrame = None, user_config: dict = None
    ) -> pd.DataFrame:

        if sleep_df is None:

            manual_sleep_df = Manual_Processor.get_sleep_df(user_config)

            sleep_df = (
                manual_sleep_df.rename(
                    columns={"wakeup": "Wake", "bedtime": "Bed", "duration": "Duration"}
                )
                .melt(id_vars="week", value_vars=["Wake", "Bed", "Duration"])
                .rename(
                    columns={
                        "week": "week_number",
                        "variable": "name",
                    }
                )
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
