from typing import Any, TypedDict

from .instruments import (
    Bond,
    Cfd,
    Commodity,
    Crypto,
    Etf,
    Future,
    Instrument,
    InstrumentType,
    Option,
    Stock,
)


class InstrumentBaseData(TypedDict):
    name: str
    symbol: str
    exchange: str | None
    currency: str
    _id: str | None
    _checksum: str | None


def create_instrument(
    type_: InstrumentType, base_data: InstrumentBaseData, details: dict[str, Any]
) -> Instrument:
    match type_:
        case InstrumentType.STOCK:
            return Stock(**base_data, isin=details["isin"])

        case InstrumentType.ETF:
            return Etf(**base_data, isin=details["isin"])

        case InstrumentType.CRYPTO:
            return Crypto(**base_data)

        case InstrumentType.COMMODITY:
            return Commodity(**base_data, unit=details["unit"])

        case InstrumentType.BOND:
            return Bond(
                **base_data,
                isin=details["isin"],
                face_value=details["face_value"],
                coupon_rate=details["coupon_rate"],
                coupon_frequency=details["coupon_frequency"],
                maturity_on=details["maturity_date"],
            )

        case InstrumentType.CFD:
            return Cfd(
                **base_data,
                underlying_instrument_id=details["underlying_instrument_id"],
                _asset_class=details["asset_class"],
                institution_id=details["institution_id"],
                leverage=details["leverage"],
            )

        case InstrumentType.FUTURE:
            return Future(
                **base_data,
                underlying_instrument_id=details["underlying_instrument_id"],
                _asset_class=details["asset_class"],
                isin=details["isin"],
                expiration_on=details["expiration_date"],
                multiplier=details["multiplier"],
            )

        case InstrumentType.OPTION:
            return Option(
                **base_data,
                underlying_instrument_id=details["underlying_instrument_id"],
                _asset_class=details["asset_class"],
                isin=details["isin"],
                expiration_on=details["expiration_date"],
                option_type=details["option_type"],
                strike_price=details["strike_price"],
                multiplier=details["multiplier"],
            )

        case _:
            raise ValueError(f"Unsupported instrument type: {type_}")
