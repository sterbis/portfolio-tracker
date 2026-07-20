import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from portfolio_tracker.domain.instrument import InstrumentType
from portfolio_tracker.domain.shared import Money
from portfolio_tracker.domain.transaction import TransactionType

from .exceptions import InstitutionReportParserError


@dataclass(frozen=True)
class ReportInstrument:
    type: InstrumentType
    name: str
    symbol: str
    currency: str
    exchange: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReportTransaction:
    external_asset_account_id: str
    external_transaction_id: str
    executed_at: datetime
    type: TransactionType
    instrument: ReportInstrument | None
    quantity: Decimal
    price: Money
    fee: Money
    tax: Money
    cash_impact: Money
    correlation_id: str | None = None


class InstitutionReportParser(ABC):
    _CASH_IMPACT_DIRECTION = {
        TransactionType.BUY: -1,
        TransactionType.DEPOSIT: 1,
        TransactionType.DIVIDEND: 1,
        TransactionType.INTEREST: 1,
        TransactionType.SELL: 1,
        TransactionType.WITHDRAWAL: -1,
    }

    def __init__(self, institution_account_id: str) -> None:
        self._institution_account_id = institution_account_id

    @abstractmethod
    def parse_report(self, report: Iterator[str]) -> Iterator[ReportTransaction]: ...

    def _to_decimal(self, value: Any) -> Decimal:
        return Decimal(str(value))

    def _to_abs_decimal(self, value: Any) -> Decimal:
        return abs(self._to_decimal(value))

    def _get_cash_impact_direction(self, transaction_type: TransactionType) -> int:
        try:
            return self._CASH_IMPACT_DIRECTION[transaction_type]
        except KeyError as error:
            raise InstitutionReportParserError(
                f"Cash impact direction not available for transaction type: {transaction_type}."
            ) from error

    def _generate_correlation_id(self) -> str:
        return f"tr_{uuid.uuid4().hex[:16]}"
