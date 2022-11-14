import datetime
import requests
import couchdb
from itertools import repeat
import pandas as pd
import numpy as np

from data_getters.utils import Data_Getter_Utils


class Marvin_Processor:

    endpoint = "https://serv.amazingmarvin.com/api/"

    def get_couch_server_db(user_config: dict):

        marvin_config = user_config["marvin_config"]

        couch = couchdb.Server(marvin_config["sync_server"])
        couch.resource.credentials = (
            marvin_config["sync_user"],
            marvin_config["sync_password"],
        )
        server_DB = couch[marvin_config["sync_database"]]

        return server_DB

    def parse_task_duration(task):

        # If this, seems like calData may be the thing to get?
        if task.get("times") is None:
            start_time = None
            end_time = None
            duration = None
        else:
            start_time = (
                None
                if len(task["times"]) == 0
                else pd.to_datetime(
                    datetime.date.fromtimestamp(
                        task["times"][0] / Data_Getter_Utils.milliseconds_in_seconds
                    )
                )
            )

            end_time = (
                None
                if len(task["times"]) == 0
                else pd.to_datetime(
                    datetime.date.fromtimestamp(
                        task["times"][1] / Data_Getter_Utils.milliseconds_in_seconds
                    )
                )
            )

            duration = task["duration"] / Data_Getter_Utils.milliseconds_in_hours

        return duration, start_time, end_time

    def get_parent_list(task, categories):

        parent_val = [item for item in categories if item["_id"] == task["parentId"]]

        if len(parent_val) == 0:
            return []

        parent = parent_val[0]
        parent_list = [parent]

        while parent["parentId"] != "root":
            parent = [item for item in categories if item["_id"] == parent["parentId"]][
                0
            ]
            parent_list.append(parent)

        return parent_list

    def parse_task(task, categories):

        parent_list = Marvin_Processor.get_parent_list(task, categories)

        if len(parent_list) == 0:
            return pd.DataFrame()

        parent_sequence = "/".join([o["title"] for o in parent_list])

        duration, start_time, end_time = Marvin_Processor.parse_task_duration(task)

        time_estimate = task.get("timeEstimate")
        time_estimate = (
            None
            if time_estimate is None
            else time_estimate / Data_Getter_Utils.milliseconds_in_hours
        )

        return pd.DataFrame(
            data={
                "name": [task["title"]],
                "day": [task["day"]],
                "time_estimate": [time_estimate],
                "parent": [parent_sequence],
                "category": [parent_list[-1]["title"]],
                "start_time": [start_time],
                "end_time": [end_time],
                "duration": [duration],
            }
        )

    def parse_habits(habit):

        habit_history = habit.get("history")

        history_df = pd.DataFrame.from_dict(
            dict(zip(habit_history[::2], habit_history[1::2])), orient="index"
        ).reset_index(drop=False)

        history_df.rename(columns={"index": "marvin_time", 0: "count"}, inplace=True)

        history_df[["id", "name", "positive", "target", "period"]] = [
            habit.get("id"),
            habit.get("title"),
            habit.get("isPositive"),
            habit.get("target"),
            habit.get("period"),
        ]

        history_df["timestamp"] = (
            history_df["marvin_time"] / Data_Getter_Utils.milliseconds_in_seconds
        ).map(datetime.date.fromtimestamp)

        history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])

        return history_df.set_index("timestamp")

    def get_marvin_task_data(user_config: dict):

        server_db = Marvin_Processor.get_couch_server_db(user_config)

        categories = list(server_db.find({"selector": {"db": "Categories"}}))
        all_tasks = server_db.find({"selector": {"db": "Tasks"}})

        task_df = pd.concat(
            map(Marvin_Processor.parse_task, all_tasks, repeat(categories))
        )
        task_df = task_df[task_df["day"] != "unassigned"]

        Data_Getter_Utils.write_temp_cache(task_df, "marvin_tasks")

    def get_marvin_habit_data(user_name: str):

        server_db = Marvin_Processor.get_couch_server_db(user_name)

        habits = list(server_db.find({"selector": {"db": "Habits"}}))

        habits_df = pd.concat(map(Marvin_Processor.parse_habits, habits))

        habits_df["week_number"] = habits_df["week_number"] = (
            pd.to_datetime(habits_df.index).isocalendar().week
        )

        habits_df.reset_index(drop=False, inplace=True)

        Data_Getter_Utils.write_temp_cache(habits_df, "marvin_habits")


class Marvin_Dashboard_Helpers:
    def format_task_df(task_df: pd.DataFrame, user_config: dict) -> pd.DataFrame:

        marvin_config = user_config["marvin_config"]
        categories_to_aggregate = marvin_config["aggregate_categories"]

        task_df = task_df[task_df["day"] != "unassigned"]
        task_df["day"] = pd.to_datetime(task_df["day"])
        task_df["month"] = task_df["day"].dt.month
        task_df["year"] = task_df["day"].dt.year

        task_df[
            ["sub_project_2", "sub_project", "main_category", "main_category_dupe"]
        ] = task_df["parent"].str.split("/", expand=True)

        task_df["end_val"] = np.where(
            task_df["category"].isin(categories_to_aggregate),
            task_df["category"],
            task_df["sub_project_2"],
        )

        task_df.drop(
            columns={
                "main_category_dupe",
                "category",
                "sub_project",
                "sub_project_2",
                "parent",
            },
            inplace=True,
        )
        task_df.rename(columns={"end_val": "category"}, inplace=True)

        return task_df

    def format_habit_df(
        habit_df: pd.DataFrame = None, user_config: dict = None
    ) -> pd.DataFrame:

        if habit_df is None:
            habit_df = Data_Getter_Utils.get_latest_file(file_prefix="marvin_habits")

        habit_df["year"] = pd.to_datetime(habit_df["timestamp"]).dt.year
        habit_df["month"] = pd.to_datetime(habit_df["timestamp"]).dt.month

        group_cols = ["name", "positive", "week_number", "year", "month"]

        # TODO handle these when get to aggreations, for now only 1
        habit_df = habit_df[habit_df["period"] == "week"]

        week_habits_df = habit_df.groupby(group_cols, as_index=False).agg(
            {"count": "sum", "target": "mean"}
        )

        return week_habits_df[group_cols + ["count", "target"]].rename(
            columns={"count": "value"}
        )
