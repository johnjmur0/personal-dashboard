import asyncio
import pytest
import pytest_asyncio
import pandas as pd
import math

from data_getters.utils import Data_Getter_Utils
from data_getters.get_marvin_data import Marvin_Processor
from data_getters.get_mint_data import Mint_API_Getter, Mint_Processor
from data_getters.get_monarch_data import Monarch_API_Getter, Monarch_Processor


@pytest.fixture(scope="session")
def user_name():
    yield "jjm"


@pytest.fixture(scope="session")
def user_config(user_name: str):
    yield Data_Getter_Utils.get_user_config(user_name)


class Test_Data_Getter_System:

    @pytest.fixture(scope="class")
    async def monarch_conn(self, user_config):

        mm_con = await Monarch_API_Getter.get_monarch_conn(user_config)
        return mm_con

    @staticmethod
    def test_marvin_conn(user_config):
        server_db = Marvin_Processor.get_couch_server_db(user_config)

        assert server_db is not None

    @pytest.mark.asyncio
    async def test_monarch_accounts(self, monarch_conn):

        accounts = await Monarch_API_Getter.get_monarch_accounts(monarch_conn)

        assert isinstance(accounts, dict)

        assert len(accounts["accounts"]) > 1

        isinstance(accounts["accounts"][0]["currentBalance"], float)

        assert abs(accounts["accounts"][0]["currentBalance"]) > 0

    @pytest.mark.asyncio
    async def test_monarch_transactions(self, monarch_conn, user_config: dict):

        transactions = await Monarch_API_Getter.get_monarch_transactions(monarch_conn)

        assert isinstance(transactions, dict)

        assert len(transactions["allTransactions"]["results"]) > 1

        transactions["allTransactions"]["results"][0]["tags"] in user_config[
            "monarch_config"
        ]["valid_tags"]

    @pytest.mark.asyncio
    async def test_monarch_budgets(self, monarch_conn):

        budgets = await Monarch_API_Getter.get_monarch_budgets(monarch_conn)

        assert isinstance(budgets, dict)

        assert (
            abs(
                budgets["budgetData"]["monthlyAmountsByCategory"][3]["monthlyAmounts"][
                    0
                ]["plannedCashFlowAmount"]
            )
            >= 0
        )

    @pytest.mark.asyncio
    async def test_monarch_transaction_df(self, monarch_conn):

        key_cols = [
            "date",
            "category",
            "account",
            "tags",
            "amount",
        ]

        transactions_df = await Monarch_API_Getter().get_monarch_transactions_df(
            monarch_conn
        )

        assert isinstance(transactions_df, pd.DataFrame)

        assert set(transactions_df.columns) == set(key_cols)

        assert len(transactions_df) > 10

        assert len(transactions_df[transactions_df["amount"].isna()]) == 0

    @pytest.mark.asycio
    async def test_monarch_budgets_df(self, monarch_conn, user_name):

        key_cols = ["meta_id", "meta_name", "type", "id", "name", "budgetAmount"]

        budget_df = await Monarch_API_Getter().get_monarch_budgets_df(
            monarch_conn, user_name=user_name
        )

        assert isinstance(budget_df, pd.DataFrame)

        assert set(budget_df.columns) == set(key_cols)

        assert len(budget_df) > 10

        assert len(budget_df[budget_df["budgetAmount"].isna()]) == 0


class Test_Data_Getter_Processors:

    @staticmethod
    def test_mint_transactions_processing(user_config, user_name):
        transactions_df = Mint_Processor.clean_transactions(
            user_config, user_name=user_name
        )

        assert len(transactions_df) > 100

        expected_cols = ["category", "day", "month", "timestamp", "total", "year"]
        assert set(expected_cols) <= set(transactions_df.columns)

        assert not math.isnan(transactions_df["total"].sum())

    @staticmethod
    def test_monarch_budget_processing(user_config, user_name):
        budget_df = Monarch_Processor.clean_budgets(user_config, user_name=user_name)

        assert len(budget_df) > 5

        expected_cols = ["category", "budget"]
        assert set(expected_cols) == set(budget_df.columns)

        assert not math.isnan(budget_df["budget"].sum())

    @staticmethod
    def test_monarch_transaction_processing(user_config):
        transactions_df = Monarch_Processor.clean_transactions(
            user_config, user_name=user_name
        )

        assert len(transactions_df) > 100

        expected_cols = ["category", "day", "month", "timestamp", "total", "year"]
        assert set(expected_cols) <= set(transactions_df.columns)

        assert not math.isnan(transactions_df["total"].sum())
