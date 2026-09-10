from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class ImportReportCommand:
    path: Path
    institution_account_id: str
    asset_account_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class SyncInstitutionAccountsCommand:
    institution_account_ids: set[str] = field(default_factory=set)
    asset_account_ids: set[str] = field(default_factory=set)
    start: datetime | None = None
    end: datetime | None = None
    restore: bool = False


@dataclass(frozen=True)
class SyncFxRatesCommand:
    dates: set[date] = field(default_factory=set)
    all: bool = False


@dataclass(frozen=True)
class SyncInstrumentsCommand:
    symbols: set[str] = field(default_factory=set)
    new_only: bool = False
    all: bool = False
