from dataclasses import dataclass
from typing import Any

from portfolio_tracker.domain.account import AssetAccount
from portfolio_tracker.domain.institution import Institution, InstitutionConnection
from portfolio_tracker.domain.instrument import (
    Bond,
    Cfd,
    Commodity,
    Etf,
    Future,
    Instrument,
    InstrumentMetadata,
    Option,
    Stock,
)
from portfolio_tracker.domain.transaction import ConvertedTransaction, Transaction
from portfolio_tracker.domain.user import User

from .account import AssetAccountView
from .institution import InstitutionConnectionView, InstitutionView
from .instrument import (
    BondView,
    CfdView,
    CommodityView,
    CryptoView,
    EtfView,
    FutureView,
    InstrumentMetadataView,
    OptionView,
    StockView,
)
from .transaction import TransactionView
from .user import UserView

type Model = type[Any]
type FieldMap = dict[str, FieldReference]


@dataclass(frozen=True)
class FieldReference:
    model: Model
    name: str


def prefix_field_map(field_map: FieldMap, prefix: str) -> FieldMap:
    return {f"{prefix}.{field_name}": field for field_name, field in field_map.items()}


USER_FIELD_MAP = {
    "id": FieldReference(User, "id"),
    "username": FieldReference(User, "username"),
}

INSTITUTION_FIELD_MAP = {
    "id": FieldReference(Institution, "id"),
    "name": FieldReference(Institution, "name"),
}

INSTITUTION_CONNECTION_FIELD_MAP = {
    "id": FieldReference(InstitutionConnection, "id"),
    "name": FieldReference(InstitutionConnection, "name"),
    "account_opened_on": FieldReference(InstitutionConnection, "account_opened_on"),
    "last_synced_at": FieldReference(InstitutionConnection, "last_synced_at"),
    **prefix_field_map(INSTITUTION_FIELD_MAP, "institution"),
}

ASSET_ACCOUNT_FIELD_MAP = {
    "id": FieldReference(AssetAccount, "id"),
    "external_id": FieldReference(AssetAccount, "external_id"),
    "name": FieldReference(AssetAccount, "name"),
    "is_active": FieldReference(AssetAccount, "is_active"),
    **prefix_field_map(INSTITUTION_CONNECTION_FIELD_MAP, "institution_connection"),
}

INSTRUMENT_FIELD_MAP = {
    "id": FieldReference(Instrument, "id"),
    "type": FieldReference(Instrument, "type"),
    "asset_class": FieldReference(Instrument, "asset_class"),
    "name": FieldReference(Instrument, "name"),
    "symbol": FieldReference(Instrument, "symbol"),
    "exchange": FieldReference(Instrument, "exchange"),
    "currency": FieldReference(Instrument, "currency"),
    "last_synced_at": FieldReference(Instrument, "last_synced_at"),
}

INSTRUMENT_METADATA_FIELD_MAP = {
    field_name: FieldReference(InstrumentMetadata, field_name)
    for field_name in INSTRUMENT_FIELD_MAP
}

BOND_DETAILS_FIELD_MAP = {
    "isin": FieldReference(Bond, "isin"),
    "face_value": FieldReference(Bond, "face_value"),
    "coupon_rate": FieldReference(Bond, "coupon_rate"),
    "coupon_frequency": FieldReference(Bond, "coupon_frequency"),
    "maturity_on": FieldReference(Bond, "maturity_on"),
}

CFD_DETAILS_FIELD_MAP = {
    "institution_id": FieldReference(Cfd, "institution_id"),
    "leverage": FieldReference(Cfd, "leverage"),
}

COMMODITY_DETAILS_FIELD_MAP = {
    "unit": FieldReference(Commodity, "unit"),
}

CRYPTO_DETAILS_FIELD_MAP: FieldMap = {}

ETF_DETAILS_FIELD_MAP = {
    "isin": FieldReference(Etf, "isin"),
}

FUTURE_DETAILS_FIELD_MAP = {
    "isin": FieldReference(Future, "isin"),
    "expiration_on": FieldReference(Future, "expiration_on"),
    "multiplier": FieldReference(Future, "multiplier"),
}

OPTION_DETAILS_FIELD_MAP = {
    "isin": FieldReference(Option, "isin"),
    "expiration_on": FieldReference(Option, "expiration_on"),
    "option_type": FieldReference(Option, "option_type"),
    "strike_price": FieldReference(Option, "strike_price"),
    "multiplier": FieldReference(Option, "multiplier"),
}

STOCK_DETAILS_FIELD_MAP = {
    "isin": FieldReference(Stock, "isin"),
}

TRANSACTION_FIELD_MAP = {
    "id": FieldReference(Transaction, "id"),
    "correlation_id": FieldReference(Transaction, "correlation_id"),
    "executed_at": FieldReference(Transaction, "executed_at"),
    "type": FieldReference(Transaction, "type"),
    "quantity": FieldReference(ConvertedTransaction, "quantity"),
    "price.native": FieldReference(ConvertedTransaction, "price.native"),
    "price.reporting": FieldReference(ConvertedTransaction, "price.reporting"),
    "fee.native": FieldReference(ConvertedTransaction, "fee.native"),
    "fee.reporting": FieldReference(ConvertedTransaction, "fee.reporting"),
    "tax.native": FieldReference(ConvertedTransaction, "tax.native"),
    "tax.reporting": FieldReference(ConvertedTransaction, "tax.reporting"),
    "cash_impact.native": FieldReference(ConvertedTransaction, "cash_impact.native"),
    "cash_impact.reporting": FieldReference(
        ConvertedTransaction, "cash_impact.reporting"
    ),
    **prefix_field_map(ASSET_ACCOUNT_FIELD_MAP, "account"),
    **prefix_field_map(INSTRUMENT_FIELD_MAP, "instrument"),
}

VIEW_REGISTRY = {
    UserView: USER_FIELD_MAP,
    InstitutionView: INSTITUTION_FIELD_MAP,
    InstitutionConnectionView: INSTITUTION_CONNECTION_FIELD_MAP,
    AssetAccountView: ASSET_ACCOUNT_FIELD_MAP,
    InstrumentMetadataView: INSTRUMENT_FIELD_MAP,
    BondView: INSTRUMENT_FIELD_MAP | BOND_DETAILS_FIELD_MAP,
    CfdView: INSTRUMENT_FIELD_MAP | CFD_DETAILS_FIELD_MAP,
    CommodityView: INSTRUMENT_FIELD_MAP | COMMODITY_DETAILS_FIELD_MAP,
    CryptoView: INSTRUMENT_FIELD_MAP | CRYPTO_DETAILS_FIELD_MAP,
    EtfView: INSTRUMENT_FIELD_MAP | ETF_DETAILS_FIELD_MAP,
    FutureView: INSTRUMENT_FIELD_MAP | FUTURE_DETAILS_FIELD_MAP,
    OptionView: INSTRUMENT_FIELD_MAP | OPTION_DETAILS_FIELD_MAP,
    StockView: INSTRUMENT_FIELD_MAP | STOCK_DETAILS_FIELD_MAP,
    TransactionView: TRANSACTION_FIELD_MAP,
}
