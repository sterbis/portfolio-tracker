from dataclasses import dataclass


@dataclass(frozen=True)
class SyncEvent: ...


@dataclass(frozen=True)
class InstitutionSyncStarted(SyncEvent):
    connection_id: str
    connection_name: str


@dataclass(frozen=True)
class InstitutionSyncCompleted(SyncEvent):
    connection_id: str
    connection_name: str


@dataclass(frozen=True)
class InstitutionSyncFailed(SyncEvent):
    connection_id: str
    connection_name: str
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
class InstrumentSyncStarted(SyncEvent):
    total: int


@dataclass(frozen=True)
class InstrumentSyncProgress(SyncEvent):
    completed: int
    total: int


@dataclass(frozen=True)
class InstrumentSyncCompleted(SyncEvent): ...


@dataclass(frozen=True)
class InstrumentSyncFailed(SyncEvent):
    error: Exception
