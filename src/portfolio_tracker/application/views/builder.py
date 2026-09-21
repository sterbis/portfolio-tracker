from typing import Iterable

from portfolio_tracker.domain.account import AssetAccount
from portfolio_tracker.domain.institution import Institution, InstitutionConnection
from portfolio_tracker.domain.instrument import (
    Bond,
    Cfd,
    Commodity,
    Crypto,
    Etf,
    Future,
    Instrument,
    InstrumentMetadata,
    Option,
    Stock,
)
from portfolio_tracker.domain.portfolio import (
    Portfolio,
    PortfolioValuation,
    ScopeType,
    ValuedPortfolio,
)
from portfolio_tracker.domain.transaction import ConvertedTransaction

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
    InstrumentView,
    OptionView,
    StockView,
)
from .portfolio import (
    CashBalanceRowView,
    PortfolioValuationView,
    PortfolioView,
    PositionRowView,
    ScopeView,
    ValuedCashBalanceView,
    ValuedPortfolioView,
)
from .transaction import TransactionView


class ViewBuilder:
    def build_institution_views(
        self, institutions: Iterable[Institution]
    ) -> dict[str, InstitutionView]:
        return {
            institution.id: InstitutionView.from_domain(institution)
            for institution in institutions
        }

    def build_institution_connection_views(
        self,
        institutions: Iterable[Institution],
        institution_connections: Iterable[InstitutionConnection],
    ) -> dict[str, InstitutionConnectionView]:
        institution_views = self.build_institution_views(institutions)
        return {
            institution_connection.id: InstitutionConnectionView.from_domain(
                institution_connection,
                institution_views[institution_connection.institution_id],
            )
            for institution_connection in institution_connections
        }

    def build_account_views(
        self,
        institutions: Iterable[Institution],
        institution_connections: Iterable[InstitutionConnection],
        accounts: Iterable[AssetAccount],
    ) -> dict[str, AssetAccountView]:
        institution_connection_views = self.build_institution_connection_views(
            institutions, institution_connections
        )
        return {
            account.id: AssetAccountView.from_domain(
                account,
                institution_connection_views[account.institution_connection_id],
            )
            for account in accounts
        }

    def build_instrument_views(
        self, instruments: Iterable[Instrument]
    ) -> dict[str, InstrumentView]:
        return {
            instrument.id: self.build_instrument_view(instrument)
            for instrument in instruments
        }

    def build_instrument_view(self, instrument: Instrument) -> InstrumentView:
        match instrument:
            case Bond() as bond:
                return BondView.from_domain(bond)

            case Cfd() as cfd:
                return CfdView.from_domain(cfd)

            case Commodity() as commodity:
                return CommodityView.from_domain(commodity)

            case Crypto() as crypto:
                return CryptoView.from_domain(crypto)

            case Etf() as etf:
                return EtfView.from_domain(etf)

            case Future() as future:
                return FutureView.from_domain(future)

            case Option() as option:
                return OptionView.from_domain(option)

            case Stock() as stock:
                return StockView.from_domain(stock)

            case _:
                raise ValueError(f"Unsupported instrument type: {type(instrument)}.")

    def build_instrument_metadata_view(
        self, metadata: InstrumentMetadata
    ) -> InstrumentMetadataView:
        return InstrumentMetadataView.from_domain(metadata)

    def build_transaction_views(
        self,
        institutions: Iterable[Institution],
        institution_connections: Iterable[InstitutionConnection],
        accounts: Iterable[AssetAccount],
        instruments: Iterable[Instrument],
        transactions: Iterable[ConvertedTransaction],
    ) -> list[TransactionView]:
        account_views = self.build_account_views(
            institutions,
            institution_connections,
            accounts,
        )
        instrument_views = self.build_instrument_views(instruments)
        return [
            TransactionView.from_domain(
                transaction,
                account_view=account_views[transaction.account_id],
                instrument_view=(
                    instrument_views[transaction.instrument_id]
                    if transaction.instrument_id
                    else None
                ),
            )
            for transaction in transactions
        ]

    def build_valued_cash_balance_views(
        self, portfolio_views: list[ValuedPortfolioView]
    ) -> dict[str | None, ValuedCashBalanceView]:
        return {
            portfolio_view.portfolio.scope.id: ValuedCashBalanceView(
                scope=portfolio_view.portfolio.scope,
                balance=portfolio_view.portfolio.cash_balance,
                valuation=(
                    portfolio_view.valuation.cash_balance
                    if portfolio_view.valuation
                    else None
                ),
            )
            for portfolio_view in portfolio_views
        }

    def build_cash_balance_row_views(
        self, portfolio_views: list[ValuedPortfolioView]
    ) -> list[CashBalanceRowView]:
        return [
            CashBalanceRowView(
                scope=portfolio_view.portfolio.scope,
                balance=balance,
            )
            for portfolio_view in portfolio_views
            for balance in portfolio_view.portfolio.cash_balance.currencies.values()
        ]

    def build_position_row_views(
        self, portfolio_views: list[ValuedPortfolioView]
    ) -> dict[str | None, PositionRowView]:
        return {
            portfolio_view.portfolio.scope.id: PositionRowView(
                scope=portfolio_view.portfolio.scope,
                position=position_view,
                valuation=(
                    portfolio_view.valuation.positions[position_view.instrument.id]
                    if portfolio_view.valuation
                    else None
                ),
            )
            for portfolio_view in portfolio_views
            for position_view in portfolio_view.portfolio.positions
        }

    def build_portfolio_views(
        self,
        institutions: Iterable[Institution],
        institution_connections: Iterable[InstitutionConnection],
        accounts: Iterable[AssetAccount],
        instruments: Iterable[Instrument],
        portfolios: Iterable[Portfolio],
    ) -> dict[str | None, PortfolioView]:
        institution_by_id = {
            institution.id: institution for institution in institutions
        }
        institution_connection_by_id = {
            institution_connection.id: institution_connection
            for institution_connection in institution_connections
        }
        account_by_id = {account.id: account for account in accounts}

        instrument_views = self.build_instrument_views(instruments)
        portfolio_views: dict[str | None, PortfolioView] = {}

        for portfolio in portfolios:
            institution = institution_connection = account = None

            if portfolio.scope.type == ScopeType.INSTITUTION:
                assert portfolio.scope.id is not None
                institution_connection = institution_connection_by_id[
                    portfolio.scope.id
                ]
                institution = institution_by_id[institution_connection.institution_id]

            if portfolio.scope.type == ScopeType.ACCOUNT:
                assert portfolio.scope.id is not None
                account = account_by_id[portfolio.scope.id]
                institution_connection = institution_connection_by_id[
                    account.institution_connection_id
                ]
                institution = institution_by_id[institution_connection.institution_id]

            scope_view = ScopeView(
                type=portfolio.scope.type,
                id=portfolio.scope.id,
                institution_name=institution.name if institution else None,
                institution_connection_name=(
                    institution_connection.name if institution_connection else None
                ),
                account_name=account.name if account else None,
            )

            portfolio_views[portfolio.scope.id] = PortfolioView.from_domain(
                portfolio, scope_view, instrument_views
            )

        return portfolio_views

    def build_portfolio_valuation_views(
        self,
        valuations: dict[str | None, PortfolioValuation],
    ) -> dict[str | None, PortfolioValuationView]:
        return {
            scope_id: PortfolioValuationView.from_domain(portfolio_valuation)
            for scope_id, portfolio_valuation in valuations.items()
        }

    def build_valued_portfolio_views(
        self,
        institutions: Iterable[Institution],
        institution_connections: Iterable[InstitutionConnection],
        accounts: Iterable[AssetAccount],
        instruments: Iterable[Instrument],
        valued_portfolios: list[ValuedPortfolio],
    ) -> dict[str | None, ValuedPortfolioView]:
        portfolio_views = self.build_portfolio_views(
            institutions,
            institution_connections,
            accounts,
            instruments,
            portfolios=[
                valued_portfolio.portfolio for valued_portfolio in valued_portfolios
            ],
        )
        return {
            valued_portfolio.portfolio.scope.id: ValuedPortfolioView(
                portfolio=portfolio_views[valued_portfolio.portfolio.scope.id],
                valuation=(
                    PortfolioValuationView.from_domain(valued_portfolio.valuation)
                    if valued_portfolio.valuation
                    else None
                ),
            )
            for valued_portfolio in valued_portfolios
        }
