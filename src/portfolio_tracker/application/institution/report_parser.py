from abc import ABC, abstractmethod

from portfolio_tracker.application.contracts.dtos import InstitutionReportDto


class InstitutionReportParser(ABC):
    @abstractmethod
    def parse_report(self, raw_data: bytes) -> InstitutionReportDto: ...
