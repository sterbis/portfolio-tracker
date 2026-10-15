# pylint: disable=protected-access

from portfolio_tracker.domain.instrument.models import Instrument


def test_instrument_id_is_deterministic(sample_stock: Instrument) -> None:
    assert sample_stock.id == "instr_a4afe411ebbf539a"


def test_instrument_identity(sample_stock: Instrument) -> None:
    assert sample_stock._identity == "STOCK|US02079K3059|GOOGL"
