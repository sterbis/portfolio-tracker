from dataclasses import dataclass
from typing import Any

from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.institution import Institution
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

from .account import AssetAccountView, InstitutionAccountView
from .institution import InstitutionView
from .instrument import (
    BondView,
    CfdView,
    CommodityView,
    CryptoView,
    EtfView,
    FutureView,
    InstrumentMetadataView,
    InstrumentView,
    OptionView,
    StockView,
)

# from .portfolio import (
#     CashBalanceValuationView,
#     CashBalanceView,
#     PortfolioView,
#     PortfolioValuationView,
#     PositionValuationView,
#     PositionView,
#     ValuedCashBalanceView,
#     ValuedPortfolioView,
#     ValuedPositionView,
# )
from .transaction import TransactionView
from .user import UserView

type Model = type[Any]
type FieldMap = dict[str, FieldReference]


@dataclass(frozen=True)
class FieldReference:
    model: Model | tuple[Model, ...]
    name: str


def prefix_field_map(field_map: FieldMap, prefix: str) -> FieldMap:
    return {f"{prefix}.{field_name}": field for field_name, field in field_map.items()}


def merge_field_maps(*field_maps: FieldMap) -> dict[str, FieldReference]:
    models_by_field: dict[str, set[Model]] = {}

    for field_map in field_maps:
        for field_name, field in field_map.items():
            models: set[Model] | tuple[Model, ...] = (
                field.model if isinstance(field.model, tuple) else (field.model,)
            )
            models_by_field.setdefault(field_name, set()).update(models)

    merged_map: FieldMap = {}

    for field_name, models in models_by_field.items():
        if len(models) == 1:
            merged_map[field_name] = FieldReference(models.pop(), field_name)
        else:
            merged_map[field_name] = FieldReference(tuple(models), field_name)

    return merged_map


USER_FIELD_MAP = {
    "id": FieldReference(User, "id"),
    "username": FieldReference(User, "username"),
}

INSTITUTION_FIELD_MAP = {
    "id": FieldReference(Institution, "id"),
    "name": FieldReference(Institution, "name"),
}

INSTITUTION_ACCOUNT_FIELD_MAP = {
    "id": FieldReference(InstitutionAccount, "id"),
    "name": FieldReference(InstitutionAccount, "name"),
    "created_on": FieldReference(InstitutionAccount, "created_on"),
    "last_synced_at": FieldReference(InstitutionAccount, "last_synced_at"),
    **prefix_field_map(INSTITUTION_FIELD_MAP, "institution"),
}

ASSET_ACCOUNT_FIELD_MAP = {
    "id": FieldReference(AssetAccount, "id"),
    "external_id": FieldReference(AssetAccount, "external_id"),
    "name": FieldReference(AssetAccount, "name"),
    "is_active": FieldReference(AssetAccount, "is_active"),
    **prefix_field_map(INSTITUTION_ACCOUNT_FIELD_MAP, "institution_account"),
}

INSTRUMENT_BASE_FIELD_MAP = {
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
    for field_name in INSTRUMENT_BASE_FIELD_MAP
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

INSTRUMENT_FIELD_MAP = {
    **INSTRUMENT_BASE_FIELD_MAP,
    **merge_field_maps(
        BOND_DETAILS_FIELD_MAP,
        CFD_DETAILS_FIELD_MAP,
        COMMODITY_DETAILS_FIELD_MAP,
        CFD_DETAILS_FIELD_MAP,
        ETF_DETAILS_FIELD_MAP,
        FUTURE_DETAILS_FIELD_MAP,
        OPTION_DETAILS_FIELD_MAP,
        STOCK_DETAILS_FIELD_MAP,
    ),
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
    "cash_impact.reporting": FieldReference(ConvertedTransaction, "cash_impact.reporting"),
    **prefix_field_map(ASSET_ACCOUNT_FIELD_MAP, "asset_account"),
    **prefix_field_map(INSTRUMENT_FIELD_MAP, "instrument"),
}

VIEW_REGISTRY = {
    UserView: USER_FIELD_MAP,
    InstitutionView: INSTITUTION_FIELD_MAP,
    InstitutionAccountView: INSTITUTION_ACCOUNT_FIELD_MAP,
    AssetAccountView: ASSET_ACCOUNT_FIELD_MAP,
    InstrumentView: INSTRUMENT_FIELD_MAP,
    InstrumentMetadataView: INSTRUMENT_METADATA_FIELD_MAP,
    BondView: INSTRUMENT_BASE_FIELD_MAP | BOND_DETAILS_FIELD_MAP,
    CfdView: INSTRUMENT_BASE_FIELD_MAP | CFD_DETAILS_FIELD_MAP,
    CommodityView: INSTRUMENT_BASE_FIELD_MAP | COMMODITY_DETAILS_FIELD_MAP,
    CryptoView: INSTRUMENT_BASE_FIELD_MAP | CRYPTO_DETAILS_FIELD_MAP,
    EtfView: INSTRUMENT_BASE_FIELD_MAP | ETF_DETAILS_FIELD_MAP,
    FutureView: INSTRUMENT_BASE_FIELD_MAP | FUTURE_DETAILS_FIELD_MAP,
    OptionView: INSTRUMENT_BASE_FIELD_MAP | OPTION_DETAILS_FIELD_MAP,
    StockView: INSTRUMENT_BASE_FIELD_MAP | STOCK_DETAILS_FIELD_MAP,
    TransactionView: TRANSACTION_FIELD_MAP,
}
