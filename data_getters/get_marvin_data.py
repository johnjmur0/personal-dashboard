import requests
import couchdb
from datetime import datetime
from itertools import repeat
import pandas as pd
import numpy as np

from utils import milliseconds_in_hours, milliseconds_in_seconds, get_user_config


class Marvin_Processor:

    endpoint = "https://serv.amazingmarvin.com/api/"

    def get_couch_server_db(username):

        user_config = get_user_config(username)
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
                    datetime.fromtimestamp(task["times"][0] / milliseconds_in_seconds)
                )
            )

            end_time = (
                None
                if len(task["times"]) == 0
                else pd.to_datetime(
                    datetime.fromtimestamp(task["times"][1] / milliseconds_in_seconds)
                )
            )

            duration = task["duration"] / milliseconds_in_hours

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
            None if time_estimate is None else time_estimate / milliseconds_in_hours
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
            history_df["marvin_time"] / milliseconds_in_seconds
        ).map(datetime.fromtimestamp)

        history_df["timestamp"] = history_df["timestamp"].dt.date

        return history_df.set_index("timestamp")

    def get_latest_data(user_name: str):

        server_db = Marvin_Processor.get_couch_server_db(user_name)

        categories = list(server_db.find({"selector": {"db": "Categories"}}))
        all_tasks = server_db.find({"selector": {"db": "Tasks"}})

        task_df = pd.concat(
            map(Marvin_Processor.parse_task, all_tasks, repeat(categories))
        )
        task_df = task_df[task_df["day"] != "unassigned"]

        date_str = datetime.now().strftime("%Y-%m-%d")
        task_df.to_csv(f"./temp_cache/marvin_tasks_{date_str}.csv", index=False)

    def get_marvin_checkin_data(user_name: str):

        server_db = Marvin_Processor.get_couch_server_db(user_name)

        habits = list(server_db.find({"selector": {"db": "Habits"}}))

        habits_df = pd.concat(map(Marvin_Processor.parse_habits, habits))

        habits_df["week_number"] = habits_df["week_number"] = (
            pd.to_datetime(habits_df.index).isocalendar().week
        )

        # for downstream
        # test_df = habits_df.groupby(
        #     ["week_number", "name", "period"], as_index=False
        # ).agg({"count": "sum", "target": "mean"})

        date_str = datetime.now().strftime("%Y-%m-%d")
        habits_df.to_csv(f"./temp_cache/marvin_habits_{date_str}.csv", index=False)


class Marvin__Dashboard_Helpers:
    def format_task_df(task_df: pd.DataFrame, user_config: dict):

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
