from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class ImportReportCommand:
    report_path: Path
    institution_account_id: str
    asset_account_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class SyncInstitutionAccountsCommand:
    user_id: str
    institution_account_ids: set[str] = field(default_factory=set)
    asset_account_ids: set[str] = field(default_factory=set)
    start: datetime | None = None
    end: datetime | None = None
    restore: bool = False

    def __post_init__(self) -> None:
        if self.institution_account_ids and self.asset_account_ids:
            raise ValueError(
                "Parameters 'institution_account_ids' and 'asset_account_ids' are mutually exclusive."
            )


@dataclass(frozen=True)
class SyncFxRatesCommand:
    dates: set[date] = field(default_factory=set)
    all: bool = False


@dataclass(frozen=True)
class SyncInstrumentsCommand:
    symbols: set[str] = field(default_factory=set)
    new_only: bool = False
    all: bool = False
