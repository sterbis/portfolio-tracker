from dataclasses import dataclass, field, fields
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.institution import Credentials, Institution, InstitutionId
from portfolio_tracker.domain.instrument import AssetClass, Instrument, InstrumentType
from portfolio_tracker.domain.portfolio import (
    ConsolidationScope,
    Portfolio,
    PortfolioValuation,
)
from portfolio_tracker.domain.portfolio.cash_balance import (
    CashBalance,
    CashBalanceValuation,
)
from portfolio_tracker.domain.portfolio.position import Position, PositionValuation
from portfolio_tracker.domain.shared import DualMoney, Money
from portfolio_tracker.domain.transaction import Transaction, TransactionType
from portfolio_tracker.domain.user import User


@dataclass(frozen=True)
class MoneyDto:
    amount: Decimal
    currency: str

    @classmethod
    def from_domain(cls, money: Money) -> MoneyDto:
        return cls(amount=money.amount, currency=money.currency)


@dataclass(frozen=True)
class DualMoneyDto:
    native: MoneyDto
    reporting: MoneyDto

    @classmethod
    def from_domain(cls, dual_money: DualMoney) -> DualMoneyDto:
        return cls(
            native=MoneyDto.from_domain(dual_money.native),
            reporting=MoneyDto.from_domain(dual_money.reporting),
        )


@dataclass(frozen=True)
class UserDto:
    id: str
    username: str

    @classmethod
    def from_domain(cls, user: User) -> UserDto:
        return cls(
            id=user.id,
            username=user.username,
        )


@dataclass(frozen=True)
class InstitutionDto:
    id: InstitutionId
    name: str
    log_in_url: str

    @classmethod
    def from_domain(cls, institution: Institution) -> InstitutionDto:
        return cls(
            id=institution.id,
            name=institution.name,
            log_in_url=institution.log_in_url,
        )


@dataclass(frozen=True)
class InstitutionAccountDto:
    id: str
    institution: InstitutionDto
    name: str
    created_on: date
    last_synced_at: datetime
    credentials: Credentials | None

    @classmethod
    def from_domain(
        cls,
        institution_account: InstitutionAccount,
        institution_dto: InstitutionDto,
        credentials: Credentials | None = None,
    ) -> InstitutionAccountDto:
        return cls(
            id=institution_account.id,
            institution=institution_dto,
            name=institution_account.name,
            created_on=institution_account.created_on,
            last_synced_at=institution_account.last_synced_at,
            credentials=credentials,
        )


@dataclass(frozen=True)
class AssetAccountDto:
    id: str
    institution_account: InstitutionAccountDto
    external_id: str
    name: str
    is_active: bool

    @classmethod
    def from_domain(
        cls,
        asset_account: AssetAccount,
        institution_account_dto: InstitutionAccountDto,
    ) -> AssetAccountDto:
        return cls(
            id=asset_account.id,
            institution_account=institution_account_dto,
            external_id=asset_account.external_id,
            name=asset_account.name,
            is_active=asset_account.is_active,
        )


@dataclass(frozen=True)
class InstitutionAccountOverviewDto:
    id: str
    institution: InstitutionDto
    name: str
    created_on: date
    last_synced_at: datetime
    credentials: Credentials | None
    asset_accounts: list[AssetAccountOverviewDto]

    @classmethod
    def from_domain(
        cls,
        institution_account: InstitutionAccount,
        institution_dto: InstitutionDto,
        asset_account_overviews: list[AssetAccountOverviewDto],
        credentials: Credentials | None = None,
    ) -> InstitutionAccountOverviewDto:
        return cls(
            id=institution_account.id,
            institution=institution_dto,
            name=institution_account.name,
            created_on=institution_account.created_on,
            last_synced_at=institution_account.last_synced_at,
            asset_accounts=asset_account_overviews,
            credentials=credentials,
        )


@dataclass(frozen=True)
class AssetAccountOverviewDto:
    id: str
    institution_account_id: str
    external_id: str
    name: str
    is_active: bool

    @classmethod
    def from_domain(
        cls,
        asset_account: AssetAccount,
    ) -> AssetAccountOverviewDto:
        return cls(
            id=asset_account.id,
            institution_account_id=asset_account.institution_account_id,
            external_id=asset_account.external_id,
            name=asset_account.name,
            is_active=asset_account.is_active,
        )


@dataclass(frozen=True)
class InstrumentDto:
    type: InstrumentType
    asset_class: AssetClass
    name: str
    symbol: str
    exchange: str | None
    currency: str
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_domain(cls, instrument: Instrument) -> InstrumentDto:
        base_fields = {field.name for field in fields(cls)} - {"details"}
        base_data = {field: getattr(instrument, field) for field in base_fields}

        instrument_fields = {field.name for field in fields(instrument)}
        details_fields = instrument_fields - base_fields
        details = {field: getattr(instrument, field) for field in details_fields}

        return cls(
            **base_data,
            details=details,
        )


@dataclass(frozen=True)
class TransactionDto:
    id: str
    executed_at: datetime
    asset_account: AssetAccountDto
    type: TransactionType
    instrument: InstrumentDto | None
    quantity: Decimal
    price: DualMoneyDto
    fee: DualMoneyDto
    tax: DualMoneyDto
    cash_impact: DualMoneyDto
    correlation_id: str | None = None

    @classmethod
    def from_domain(
        cls,
        transaction: Transaction,
        rates: FxRates,
        reporting_currency: str,
        asset_account_dto: AssetAccountDto,
        instrument_dto: InstrumentDto | None = None,
    ) -> TransactionDto:
        transaction.price.convert(reporting_currency, rates)

        return cls(
            id=transaction.id,
            executed_at=transaction.executed_at,
            asset_account=asset_account_dto,
            type=transaction.type,
            instrument=instrument_dto,
            quantity=transaction.quantity,
            price=DualMoneyDto(
                native=MoneyDto.from_domain(transaction.price),
                reporting=MoneyDto.from_domain(
                    transaction.price.convert(reporting_currency, rates)
                ),
            ),
            fee=DualMoneyDto(
                native=MoneyDto.from_domain(transaction.fee),
                reporting=MoneyDto.from_domain(
                    transaction.fee.convert(reporting_currency, rates)
                ),
            ),
            tax=DualMoneyDto(
                native=MoneyDto.from_domain(transaction.tax),
                reporting=MoneyDto.from_domain(
                    transaction.tax.convert(reporting_currency, rates)
                ),
            ),
            cash_impact=DualMoneyDto(
                native=MoneyDto.from_domain(transaction.cash_impact),
                reporting=MoneyDto.from_domain(
                    transaction.cash_impact.convert(reporting_currency, rates)
                ),
            ),
            correlation_id=transaction.correlation_id,
        )


@dataclass(frozen=True)
class PositionDto:
    instrument: InstrumentDto

    quantity: Decimal
    cost_basis: DualMoneyDto
    average_price: DualMoneyDto
    fees: DualMoneyDto

    opened_at: datetime
    last_trade_at: datetime
    last_trade_type: str
    last_buy_at: datetime | None
    closed_at: datetime | None

    is_closed: bool
    is_tax_free: bool

    tax_free_position: PositionDto | None

    @classmethod
    def from_domain(
        cls,
        position: Position,
        instrument_dto: InstrumentDto,
    ) -> PositionDto:
        return cls(
            instrument=instrument_dto,
            quantity=position.quantity,
            cost_basis=DualMoneyDto.from_domain(position.cost_basis),
            average_price=DualMoneyDto.from_domain(position.average_price),
            fees=DualMoneyDto.from_domain(position.fees),
            opened_at=position.opened_at,
            last_trade_at=position.last_trade_at,
            last_trade_type=position.last_trade_type,
            last_buy_at=position.last_buy_at,
            closed_at=position.closed_at,
            is_closed=position.is_closed,
            is_tax_free=position.is_tax_free,
            tax_free_position=(
                PositionDto.from_domain(position.tax_free_position, instrument_dto)
                if position.tax_free_position
                else None
            ),
        )


@dataclass(frozen=True)
class PositionValuationDto:
    market_price: DualMoneyDto
    market_value: DualMoneyDto
    unrealized_pnl: DualMoneyDto
    native_unrealized_pnl_percent: Decimal | None
    reporting_unrealized_pnl_percent: Decimal | None

    tax_free_valuation: PositionValuationDto | None

    @classmethod
    def from_domain(
        cls,
        valuation: PositionValuation,
    ) -> PositionValuationDto:
        return cls(
            market_price=DualMoneyDto.from_domain(valuation.market_price),
            market_value=DualMoneyDto.from_domain(valuation.market_value),
            unrealized_pnl=DualMoneyDto.from_domain(valuation.unrealized_pnl),
            native_unrealized_pnl_percent=valuation.native_unrealized_pnl_percent,
            reporting_unrealized_pnl_percent=valuation.reporting_unrealized_pnl_percent,
            tax_free_valuation=(
                PositionValuationDto.from_domain(valuation.tax_free_valuation)
                if valuation.tax_free_valuation
                else None
            ),
        )


@dataclass(frozen=True)
class ValuedPositionDto:
    position: PositionDto
    valuation: PositionValuationDto | None


@dataclass(frozen=True)
class CashBalanceDto:
    currencies: dict[str, MoneyDto]

    @classmethod
    def from_domain(cls, cash_balance: CashBalance) -> CashBalanceDto:
        return cls(
            currencies={
                currency: MoneyDto.from_domain(balance)
                for currency, balance in cash_balance.currencies.items()
            }
        )


@dataclass(frozen=True)
class CashBalanceValuationDto:
    total_balance: MoneyDto

    @classmethod
    def from_domain(cls, valuation: CashBalanceValuation) -> CashBalanceValuationDto:
        return cls(
            total_balance=MoneyDto.from_domain(valuation.total_balance),
        )


@dataclass(frozen=True)
class ValuedCashBalanceDto:
    cash_balance: CashBalanceDto
    valuation: CashBalanceValuationDto


@dataclass(frozen=True)
class PortfolioDto:
    scope: ConsolidationScope
    account: AssetAccountDto | InstitutionAccountDto | None
    reporting_currency: str
    positions: list[PositionDto]
    cash_balance: CashBalanceDto

    @classmethod
    def from_domain(
        cls,
        portfolio: Portfolio,
        account_dto: AssetAccountDto | InstitutionAccountDto | None,
        instrument_dtos: dict[str, InstrumentDto],
    ) -> PortfolioDto:
        return cls(
            scope=portfolio.scope,
            account=account_dto,
            reporting_currency=portfolio.reporting_currency,
            positions=[
                PositionDto.from_domain(
                    position, instrument_dtos[position.instrument_id]
                )
                for position in portfolio.positions
            ],
            cash_balance=CashBalanceDto.from_domain(portfolio.cash_balance),
        )


@dataclass(frozen=True)
class PortfolioValuationDto:
    account_id: str | None

    positions: dict[str, PositionValuationDto]
    cash_balance: CashBalanceValuationDto

    market_value: MoneyDto
    unrealized_pnl: MoneyDto
    asset_allocation: dict[AssetClass, tuple[MoneyDto, Decimal | None]]
    instrument_type_allocation: dict[InstrumentType, tuple[MoneyDto, Decimal | None]]

    is_partially_valued: bool = True

    @classmethod
    def from_domain(cls, valuation: PortfolioValuation) -> PortfolioValuationDto:
        return cls(
            account_id=valuation.account_id,
            positions={
                instrument_id: PositionValuationDto.from_domain(position_valuation)
                for instrument_id, position_valuation in valuation.positions.items()
            },
            cash_balance=CashBalanceValuationDto.from_domain(valuation.cash_balance),
            market_value=MoneyDto.from_domain(valuation.market_value),
            unrealized_pnl=MoneyDto.from_domain(valuation.unrealized_pnl),
            asset_allocation={
                asset_class: (MoneyDto.from_domain(market_value), weight)
                for asset_class, (
                    market_value,
                    weight,
                ) in valuation.asset_allocation.items()
            },
            instrument_type_allocation={
                instrument_type: (MoneyDto.from_domain(market_value), weight)
                for instrument_type, (
                    market_value,
                    weight,
                ) in valuation.instrument_type_allocation.items()
            },
            is_partially_valued=valuation.is_partially_valued,
        )


@dataclass(frozen=True)
class ValuedPortfolioDto:
    portfolio: PortfolioDto
    valuation: PortfolioValuationDto | None
