import pytest
import math

from data_getters.utils import Data_Getter_Utils
from data_getters.get_marvin_data import Marvin_Processor
from data_getters.get_mint_data import Mint_API_Getter, Mint_Processor


@pytest.fixture(sope="session")
def user_config():
    yield Data_Getter_Utils.get_user_config("jjm")


class Test_Data_Getter_System:
    @staticmethod
    def test_marvin_conn(user_config):
        server_db = Marvin_Processor.get_couch_server_db(user_config)

        assert server_db is not None

    @staticmethod
    def test_monarch_conn(user_config):
        assert False


class Test_Data_Getter_Processors:
    @staticmethod
    def test_mint_transactions_processing(user_config):
        transactions_df = Mint_Processor.clean_transactions(user_config)

        assert len(transactions_df) > 100

        expected_cols = ["year", "month", "category", "amount"]
        assert set(expected_cols) <= set(transactions_df.columns)

        assert not math.isnan(transactions_df["amount"].sum())
