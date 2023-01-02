import pandas as pd
from plotnine import ggplot, aes, facet_wrap, geom_col

from data_getters.utils import Data_Getter_Utils


class Budget_Analysis_Helpers:
    def join_user_df(
        base_df: pd.DataFrame, file_prefix: str, user_id: str
    ) -> pd.DataFrame:

        user_df = Data_Getter_Utils.get_latest_file(
            file_prefix=f"{file_prefix}_{user_id}"
        )
        user_df["user"] = user_id
        base_df = pd.concat([base_df, user_df])

        return base_df

    def create_fwd_df_single(
        input_df: pd.DataFrame, col_name: str, percentiles=["mean", "25%"]
    ) -> pd.DataFrame:

        input_df = (
            input_df.groupby(["user"], as_index=True)[["total"]]
            .describe()
            .stack(level=0)[percentiles]
        )

        input_df = (
            input_df.reset_index(drop=False)
            .drop(columns={"level_1"})
            .melt(id_vars=["user"])
        )

        return input_df.rename(columns={"value": col_name})

    def create_fwd_df_all(monthly_df: pd.DataFrame) -> pd.DataFrame:

        fwd_spend_df = Budget_Analysis_Helpers.create_fwd_df_single(
            monthly_df[~monthly_df["category"].isin(["paycheck", "bonus"])]
            .groupby(["user", "timestamp", "year", "month"], as_index=False)
            .agg({"total": "sum"}),
            "spending",
        )

        fwd_income_df = Budget_Analysis_Helpers.create_fwd_df_single(
            monthly_df[monthly_df["category"].isin(["paycheck"])],
            "income",
        )

        fwd_profit_df = Budget_Analysis_Helpers.create_fwd_df_single(
            monthly_df[monthly_df["category"] != "bonus"]
            .groupby(["user", "timestamp"], as_index=False)
            .agg({"total": "sum"}),
            "profit",
        )

        return fwd_spend_df.merge(fwd_income_df).merge(fwd_profit_df)


if __name__ == "__main__":

    users = ["jjm", "dmg"]

    account_df = pd.DataFrame()
    finance_df = pd.DataFrame()
    budget_df = pd.DataFrame()

    for user in users:

        account_df = Budget_Analysis_Helpers.join_user_df(
            account_df, "account_totals", user
        )
        budget_df = Budget_Analysis_Helpers.join_user_df(
            budget_df, "monthly_budget", user
        )
        finance_df = Budget_Analysis_Helpers.join_user_df(
            finance_df, "daily_finances", user
        )

    monthly_df = finance_df.groupby(
        ["year", "month", "category", "user"], as_index=False
    ).agg({"total": "sum"})
    monthly_df["day"] = 1
    monthly_df["timestamp"] = pd.to_datetime(monthly_df[["year", "month", "day"]])

    # Join budget here for less repetition?
    monthly_df = monthly_df[monthly_df["year"] >= 2021]
    total_budget = budget_df.groupby(["user"]).agg({"budget": "sum"})

    all_fwd_df = Budget_Analysis_Helpers.create_fwd_df_all(monthly_df)

    pass
