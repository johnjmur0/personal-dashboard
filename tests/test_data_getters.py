import asyncio
import pytest
import pytest_asyncio
import math

from data_getters.utils import Data_Getter_Utils
from data_getters.get_marvin_data import Marvin_Processor
from data_getters.get_mint_data import Mint_API_Getter, Mint_Processor
from data_getters.get_monarch_data import Monarch_API_Getter


@pytest.fixture(scope="session")
def user_config():
    yield Data_Getter_Utils.get_user_config("jjm")


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

        transactions["allTransactions"]["results"][0]["tags"] in user_config["monarch_config"]["valid_tags"]


class Test_Data_Getter_Processors:
    @staticmethod
    def test_mint_transactions_processing(user_config):
        transactions_df = Mint_Processor.clean_transactions(user_config)

        assert len(transactions_df) > 100

        expected_cols = ["year", "month", "category", "amount"]
        assert set(expected_cols) <= set(transactions_df.columns)

        assert not math.isnan(transactions_df["amount"].sum())
