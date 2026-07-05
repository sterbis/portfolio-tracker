import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from datetime import date
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
    type: InstrumentType
    asset_class: AssetClass
    name: str
    symbol: str
    exchange: str | None
    currency: str


@dataclass(frozen=True)
class Instrument(ABC):
    name: str
    symbol: str
    exchange: str | None
    currency: str
    _id: str | None

    @property
    def id(self) -> str:
        assert self._id is not None
        return self._id

    @property
    @abstractmethod
    def type(self) -> InstrumentType: ...

    @property
    @abstractmethod
    def asset_class(self) -> AssetClass: ...

    @property
    def metadata(self) -> InstrumentMetadata:
        return InstrumentMetadata(
            **{
                field_.name: getattr(self, field_.name)
                for field_ in fields(InstrumentMetadata)
            }
        )

    def __post_init__(self) -> None:
        hash_string = f"{self.type.value}|{self._identifier}"
        hash_digest = hashlib.sha256(hash_string.encode("utf-8")).hexdigest()[:16]
        instrument_id = f"ins_{hash_digest}"

        if self._id is None:
            object.__setattr__(self, "_id", instrument_id)

        elif self._id != instrument_id:
            raise ValueError(
                f"Provided instrument id {self._id} does not match generated id {instrument_id}."
            )

    @property
    @abstractmethod
    def _identifier(self) -> str: ...


@dataclass(frozen=True)
class DerivativeInstrument(Instrument):
    underlying_instrument_id: str
    _asset_class: AssetClass

    @property
    def asset_class(self) -> AssetClass:
        return self._asset_class


@dataclass(frozen=True)
class Bond(Instrument):
    isin: str
    face_value: Decimal
    coupon_rate: Decimal
    coupon_frequency: CouponFrequency
    maturity_on: date

    @property
    def type(self) -> InstrumentType:
        return InstrumentType.BOND

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.CASH

    @property
    def _identifier(self) -> str:
        return f"{self.isin}|{self.symbol}"


@dataclass(frozen=True)
class Cfd(DerivativeInstrument):
    institution_id: str
    leverage: Decimal

    @property
    def type(self) -> InstrumentType:
        return InstrumentType.CFD

    @property
    def _identifier(self) -> str:
        return f"{self.institution_id}|{self.symbol}"


@dataclass(frozen=True)
class Commodity(Instrument):
    unit: str

    @property
    def type(self) -> InstrumentType:
        return InstrumentType.COMMODITY

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.COMMODITY

    @property
    def _identifier(self) -> str:
        return f"{self.symbol}|{self.unit}"


@dataclass(frozen=True)
class Crypto(Instrument):
    @property
    def type(self) -> InstrumentType:
        return InstrumentType.CRYPTO

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.CRYPTO

    @property
    def _identifier(self) -> str:
        return f"{self.symbol}|{self.currency}"


@dataclass(frozen=True)
class Etf(Instrument):
    isin: str

    @property
    def type(self) -> InstrumentType:
        return InstrumentType.ETF

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.EQUITY

    @property
    def _identifier(self) -> str:
        return f"{self.isin}|{self.symbol}"


@dataclass(frozen=True)
class Future(DerivativeInstrument):
    isin: str | None
    expiration_on: date
    multiplier: int

    @property
    def type(self) -> InstrumentType:
        return InstrumentType.FUTURE

    @property
    def _identifier(self) -> str:
        return f"{self.isin}|{self.symbol}"


@dataclass(frozen=True)
class Option(DerivativeInstrument):
    isin: str | None
    expiration_on: date
    option_type: OptionType
    strike_price: Decimal
    multiplier: int

    @property
    def type(self) -> InstrumentType:
        return InstrumentType.OPTION

    @property
    def _identifier(self) -> str:
        return f"{self.isin}|{self.symbol}"


@dataclass(frozen=True)
class Stock(Instrument):
    isin: str

    @property
    def type(self) -> InstrumentType:
        return InstrumentType.STOCK

    @property
    def asset_class(self) -> AssetClass:
        return AssetClass.EQUITY

    @property
    def _identifier(self) -> str:
        return f"{self.isin}|{self.symbol}"
