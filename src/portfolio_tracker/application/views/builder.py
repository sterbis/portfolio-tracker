from typing import Iterable

from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.institution import Institution
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
    ConsolidationScope,
    Portfolio,
    PortfolioValuation,
)
from portfolio_tracker.domain.transaction import ConvertedTransaction

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
from .portfolio import PortfolioValuationView, PortfolioView, ValuedPortfolioView
from .transaction import TransactionView


class ViewBuilder:
    def build_institution_views(
        self, institutions: Iterable[Institution]
    ) -> dict[str, InstitutionView]:
        return {
            institution.id: InstitutionView.from_domain(institution)
            for institution in institutions
        }

    def build_institution_account_views(
        self,
        institutions: Iterable[Institution],
        institution_accounts: Iterable[InstitutionAccount],
    ) -> dict[str, InstitutionAccountView]:
        institution_views = self.build_institution_views(institutions)
        return {
            institution_account.id: InstitutionAccountView.from_domain(
                institution_account,
                institution_views[institution_account.institution_id],
            )
            for institution_account in institution_accounts
        }

    def build_asset_account_views(
        self,
        institutions: Iterable[Institution],
        institution_accounts: Iterable[InstitutionAccount],
        asset_accounts: Iterable[AssetAccount],
    ) -> dict[str, AssetAccountView]:
        institution_account_views = self.build_institution_account_views(
            institutions, institution_accounts
        )
        return {
            asset_account.id: AssetAccountView.from_domain(
                asset_account,
                institution_account_views[asset_account.institution_account_id],
            )
            for asset_account in asset_accounts
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
        institution_accounts: Iterable[InstitutionAccount],
        asset_accounts: Iterable[AssetAccount],
        instruments: Iterable[Instrument],
        transactions: Iterable[ConvertedTransaction],
    ) -> list[TransactionView]:
        asset_account_views = self.build_asset_account_views(
            institutions,
            institution_accounts,
            asset_accounts,
        )
        instrument_views = self.build_instrument_views(instruments)
        return [
            TransactionView.from_domain(
                transaction,
                asset_account_view=asset_account_views[transaction.asset_account_id],
                instrument_view=(
                    instrument_views[transaction.instrument_id]
                    if transaction.instrument_id
                    else None
                ),
            )
            for transaction in transactions
        ]

    def build_portfolio_views(
        self,
        institutions: Iterable[Institution],
        institution_accounts: Iterable[InstitutionAccount],
        asset_accounts: Iterable[AssetAccount],
        instruments: Iterable[Instrument],
        portfolios: Iterable[Portfolio],
    ) -> list[PortfolioView]:
        asset_account_views = self.build_asset_account_views(
            institutions,
            institution_accounts,
            asset_accounts,
        )
        institution_account_views = {
            asset_account_dto.institution_account.id: asset_account_dto.institution_account
            for asset_account_dto in asset_account_views.values()
        }
        instrument_views = self.build_instrument_views(instruments)
        portfolio_views: list[PortfolioView] = []

        for portfolio in portfolios:
            account_view: AssetAccountView | InstitutionAccountView | None = None
            if portfolio.scope == ConsolidationScope.ASSET_ACCOUNT:
                assert portfolio.account_id is not None
                account_view = asset_account_views[portfolio.account_id]
            elif portfolio.scope == ConsolidationScope.INSTITUTION_ACCOUNT:
                assert portfolio.account_id is not None
                account_view = institution_account_views[portfolio.account_id]

            portfolio_views.append(
                PortfolioView.from_domain(portfolio, account_view, instrument_views)
            )

        return portfolio_views

    def build_portfolio_valuation_views(
        self,
        portfolio_valuations: dict[str | None, PortfolioValuation],
    ) -> dict[str | None, PortfolioValuationView]:
        return {
            account_id: PortfolioValuationView.from_domain(portfolio_valuation)
            for account_id, portfolio_valuation in portfolio_valuations.items()
        }

    def build_valued_portfolio_views(
        self,
        institutions: Iterable[Institution],
        institution_accounts: Iterable[InstitutionAccount],
        asset_accounts: Iterable[AssetAccount],
        instruments: Iterable[Instrument],
        portfolios: Iterable[Portfolio],
        portfolio_valuations: dict[str | None, PortfolioValuation],
    ) -> list[ValuedPortfolioView]:
        portfolio_views = self.build_portfolio_views(
            institutions,
            institution_accounts,
            asset_accounts,
            instruments,
            portfolios,
        )
        portfolio_valuation_views = self.build_portfolio_valuation_views(
            portfolio_valuations
        )
        return [
            ValuedPortfolioView(
                portfolio_dto,
                portfolio_valuation_views.get(
                    portfolio_dto.account.id if portfolio_dto.account else None
                ),
            )
            for portfolio_dto in portfolio_views
        ]
