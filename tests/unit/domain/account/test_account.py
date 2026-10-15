# pylint: disable=protected-access

from portfolio_tracker.domain.account.models import AssetAccount


def test_account_id_is_deterministic(sample_account: AssetAccount) -> None:
    assert sample_account.id == "acc_d81749a412c9be7c"


def test_account_identity(sample_account: AssetAccount) -> None:
    assert sample_account._identity == "conn_001|3210123"
