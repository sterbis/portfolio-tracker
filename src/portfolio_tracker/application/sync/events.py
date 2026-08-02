from dataclasses import dataclass


@dataclass(frozen=True)
class SyncEvent: ...


@dataclass(frozen=True)
class InstitutionAccountSyncStarted(SyncEvent):
    account_id: str
    account_name: str


@dataclass(frozen=True)
class InstitutionAccountSyncCompleted(SyncEvent):
    account_id: str
    account_name: str


@dataclass(frozen=True)
class InstitutionAccountSyncFailed(SyncEvent):
    account_id: str
    account_name: str
    error: Exception


@dataclass(frozen=True)
class FxSyncStarted(SyncEvent):
    total: int


@dataclass(frozen=True)
class FxSyncProgress(SyncEvent):
    completed: int
    total: int


@dataclass(frozen=True)
class FxSyncCompleted(SyncEvent): ...


@dataclass(frozen=True)
class FxSyncFailed(SyncEvent):
    error: Exception


@dataclass(frozen=True)
class InstrumentsSyncStarted(SyncEvent):
    total: int


@dataclass(frozen=True)
class InstrumentsSyncProgress(SyncEvent):
    completed: int
    total: int


@dataclass(frozen=True)
class InstrumentsSyncCompleted(SyncEvent): ...


@dataclass(frozen=True)
class InstrumentsSyncFailed(SyncEvent):
    error: Exception
