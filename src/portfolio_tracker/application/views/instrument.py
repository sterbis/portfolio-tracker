from abc import ABC
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from portfolio_tracker.domain.instrument import (
    AssetClass,
    Bond,
    Cfd,
    Commodity,
    CouponFrequency,
    Crypto,
    Etf,
    Future,
    Instrument,
    InstrumentMetadata,
    InstrumentType,
    Option,
    OptionType,
    Stock,
)


@dataclass(frozen=True, kw_only=True)
class InstrumentView(ABC):
    id: str
    type: InstrumentType
    asset_class: AssetClass
    name: str
    symbol: str
    exchange: str | None = None
    currency: str
    last_synced_at: datetime | None = None

    @staticmethod
    def _base_data(instrument: Instrument | InstrumentMetadata) -> dict[str, Any]:
        return {
            "id": instrument.id,
            "type": instrument.type,
            "asset_class": instrument.asset_class,
            "name": instrument.name,
            "symbol": instrument.symbol,
            "exchange": instrument.exchange,
            "currency": instrument.currency,
            "last_synced_at": instrument.last_synced_at,
        }


@dataclass(frozen=True, kw_only=True)
class InstrumentMetadataView(InstrumentView):
    id: str
    type: InstrumentType
    asset_class: AssetClass
    name: str
    symbol: str
    exchange: str | None = None
    currency: str
    last_synced_at: datetime | None = None

    @classmethod
    def from_domain(cls, metadata: InstrumentMetadata) -> InstrumentMetadataView:
        return cls(
            **cls._base_data(metadata),
        )


@dataclass(frozen=True, kw_only=True)
class BondView(InstrumentView):
    isin: str
    face_value: Decimal
    coupon_rate: Decimal
    coupon_frequency: CouponFrequency
    maturity_on: date

    @classmethod
    def from_domain(cls, bond: Bond) -> BondView:
        return cls(
            **cls._base_data(bond),
            isin=bond.isin,
            face_value=bond.face_value,
            coupon_rate=bond.coupon_rate,
            coupon_frequency=bond.coupon_frequency,
            maturity_on=bond.maturity_on,
        )


@dataclass(frozen=True, kw_only=True)
class CfdView(InstrumentView):
    institution_id: str
    leverage: Decimal

    @classmethod
    def from_domain(cls, cfd: Cfd) -> CfdView:
        return cls(
            **cls._base_data(cfd),
            institution_id=cfd.institution_id,
            leverage=cfd.leverage,
        )


@dataclass(frozen=True, kw_only=True)
class CommodityView(InstrumentView):
    unit: str

    @classmethod
    def from_domain(cls, commodity: Commodity) -> CommodityView:
        return cls(
            **cls._base_data(commodity),
            unit=commodity.unit,
        )


@dataclass(frozen=True, kw_only=True)
class CryptoView(InstrumentView):
    @classmethod
    def from_domain(cls, crypto: Crypto) -> CryptoView:
        return cls(
            **cls._base_data(crypto),
        )


@dataclass(frozen=True, kw_only=True)
class EtfView(InstrumentView):
    isin: str

    @classmethod
    def from_domain(cls, etf: Etf) -> EtfView:
        return cls(
            **cls._base_data(etf),
            isin=etf.isin,
        )


@dataclass(frozen=True, kw_only=True)
class FutureView(InstrumentView):
    isin: str | None = None
    expiration_on: date
    multiplier: int

    @classmethod
    def from_domain(cls, future: Future) -> FutureView:
        return cls(
            **cls._base_data(future),
            isin=future.isin,
            expiration_on=future.expiration_on,
            multiplier=future.multiplier,
        )


@dataclass(frozen=True, kw_only=True)
class OptionView(InstrumentView):
    isin: str | None = None
    expiration_on: date
    option_type: OptionType
    strike_price: Decimal
    multiplier: int

    @classmethod
    def from_domain(cls, option: Option) -> OptionView:
        return cls(
            **cls._base_data(option),
            isin=option.isin,
            expiration_on=option.expiration_on,
            option_type=option.option_type,
            strike_price=option.strike_price,
            multiplier=option.multiplier,
        )


@dataclass(frozen=True, kw_only=True)
class StockView(InstrumentView):
    isin: str

    @classmethod
    def from_domain(cls, stock: Stock) -> StockView:
        return cls(
            **cls._base_data(stock),
            isin=stock.isin,
        )
