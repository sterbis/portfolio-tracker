import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class AssetClass(StrEnum):
    BOND = "BOND"
    CASH = "CASH"
    COMMODITY = "COMMODITY"
    CRYPTO = "CRYPTO"
    EQUITY = "EQUITY"
    REAL_ESTATE = "REAL_ESTATE"


class InstrumentType(StrEnum):
    BOND = "BOND"
    CFD = "CFD"
    COMMODITY = "COMMODITY"
    CRYPTO = "CRYPTO"
    ETF = "ETF"
    FUTURE = "FUTURE"
    INDEX = "INDEX"
    MUTUAL_FUND = "MUTUAL_FUND"
    OPTION = "OPTION"
    PROPERTY = "PROPERTY"
    SAVINGS_ACCOUNT = "SAVINGS_ACCOUNT"
    STOCK = "STOCK"

    @property
    def is_derivative(self) -> bool:
        return self in (
            InstrumentType.CFD,
            InstrumentType.FUTURE,
            InstrumentType.OPTION,
        )


class CouponFrequency(StrEnum):
    ANNUAL = "ANNUAL"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUAL = "SEMI_ANNUAL"


class OptionType(StrEnum):
    CALL = "CALL"
    PUT = "PUT"


@dataclass(frozen=True)
class InstrumentMetadata:
    id: str
    checksum: str
    type: InstrumentType
    asset_class: AssetClass
    name: str
    symbol: str
    exchange: str | None
    currency: str
    last_synced_at: datetime | None


@dataclass(frozen=True, kw_only=True)
class Instrument(ABC):
    id: str = field(default_factory=lambda: f"instr_{uuid.uuid4().hex[:16]}")
    checksum: str | None = None
    type: InstrumentType
    asset_class: AssetClass
    name: str
    symbol: str
    exchange: str | None = None
    currency: str
    last_synced_at: datetime | None = None

    @property
    @abstractmethod
    def _identifier(self) -> str: ...

    @property
    def metadata(self) -> InstrumentMetadata:
        return InstrumentMetadata(
            **{
                field_.name: getattr(self, field_.name)
                for field_ in fields(InstrumentMetadata)
            }
        )

    def __post_init__(self) -> None:
        checksum_string = f"{self.type.value}|{self._identifier}"
        checksum = hashlib.sha256(checksum_string.encode("utf-8")).hexdigest()[:16]

        if self.checksum is None:
            object.__setattr__(self, "checksum", checksum)

        elif self.checksum != checksum:
            raise ValueError(
                f"Provided instrument checksum {self.checksum} does not match computed checksum {checksum}."
            )


@dataclass(frozen=True, kw_only=True)
class DerivativeInstrument(Instrument):
    underlying_instrument_id: str


@dataclass(frozen=True, kw_only=True)
class Bond(Instrument):
    type: InstrumentType = field(init=False, default=InstrumentType.BOND)
    asset_class: AssetClass = field(init=False, default=AssetClass.CASH)
    isin: str
    face_value: Decimal
    coupon_rate: Decimal
    coupon_frequency: CouponFrequency
    maturity_on: date

    @property
    def _identifier(self) -> str:
        return f"{self.isin}|{self.symbol}"


@dataclass(frozen=True, kw_only=True)
class Cfd(DerivativeInstrument):
    type: InstrumentType = field(init=False, default=InstrumentType.CFD)
    institution_id: str
    leverage: Decimal

    @property
    def _identifier(self) -> str:
        return f"{self.institution_id}|{self.symbol}"


@dataclass(frozen=True, kw_only=True)
class Commodity(Instrument):
    type: InstrumentType = field(init=False, default=InstrumentType.COMMODITY)
    asset_class: AssetClass = field(init=False, default=AssetClass.COMMODITY)
    unit: str

    @property
    def _identifier(self) -> str:
        return f"{self.symbol}|{self.unit}"


@dataclass(frozen=True, kw_only=True)
class Crypto(Instrument):
    type: InstrumentType = field(init=False, default=InstrumentType.CRYPTO)
    asset_class: AssetClass = field(init=False, default=AssetClass.CRYPTO)

    @property
    def _identifier(self) -> str:
        return f"{self.symbol}|{self.currency}"


@dataclass(frozen=True, kw_only=True)
class Etf(Instrument):
    type: InstrumentType = field(init=False, default=InstrumentType.ETF)
    asset_class: AssetClass = field(init=False, default=AssetClass.EQUITY)
    isin: str

    @property
    def _identifier(self) -> str:
        return f"{self.isin}|{self.symbol}"


@dataclass(frozen=True, kw_only=True)
class Future(DerivativeInstrument):
    type: InstrumentType = field(init=False, default=InstrumentType.FUTURE)
    isin: str | None = None
    expiration_on: date
    multiplier: int

    @property
    def _identifier(self) -> str:
        return f"{self.isin}|{self.symbol}"


@dataclass(frozen=True, kw_only=True)
class Option(DerivativeInstrument):
    type: InstrumentType = field(init=False, default=InstrumentType.OPTION)
    isin: str | None = None
    expiration_on: date
    option_type: OptionType
    strike_price: Decimal
    multiplier: int

    @property
    def _identifier(self) -> str:
        return f"{self.isin}|{self.symbol}"


@dataclass(frozen=True, kw_only=True)
class Stock(Instrument):
    type: InstrumentType = field(init=False, default=InstrumentType.ETF)
    asset_class: AssetClass = field(init=False, default=AssetClass.EQUITY)
    isin: str

    @property
    def _identifier(self) -> str:
        return f"{self.isin}|{self.symbol}"
