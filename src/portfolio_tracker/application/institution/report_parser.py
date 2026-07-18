from abc import ABC, abstractmethod
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

from portfolio_tracker.application.contracts.dtos import ReportTransactionDto


class InstitutionReportParser(ABC):
    def __init__(self, institution_account_id: str) -> None:
        self._institution_account_id = institution_account_id

    @abstractmethod
    def parse_report(self, report: Iterator[str]) -> Iterator[ReportTransactionDto]: ...

    def _to_decimal(self, value: Any) -> Decimal:
        return Decimal(str(value))
    
    def _to_abs_decimal(self, value: Any) -> Decimal:
        return abs(self._to_decimal(value))
