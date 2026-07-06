from datetime import date

from portfolio_tracker.domain.account import AssetAccount, InstitutionAccount
from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.institution import Institution
from portfolio_tracker.domain.instrument import Instrument
from portfolio_tracker.domain.portfolio import (
    ConsolidationScope,
    Portfolio,
    PortfolioValuation,
)
from portfolio_tracker.domain.transaction import Transaction

from .dtos import (
    AssetAccountDto,
    InstitutionAccountDto,
    InstitutionDto,
    InstrumentDto,
    PortfolioDto,
    PortfolioValuationDto,
    TransactionDto,
    ValuedPortfolioDto,
)


class DtoAssembler:
    @classmethod
    def assemble_institutions(
        cls,
        institutions: list[Institution],
    ) -> dict[str, InstitutionDto]:
        return {
            institution.id: InstitutionDto.from_domain(institution)
            for institution in institutions
        }

    @classmethod
    def assemble_institution_accounts(
        cls,
        institutions: list[Institution],
        institution_accounts: list[InstitutionAccount],
    ) -> dict[str, InstitutionAccountDto]:
        institution_dtos = cls.assemble_institutions(institutions)
        return {
            institution_account.id: InstitutionAccountDto.from_domain(
                institution_account,
                institution_dtos[institution_account.institution_id],
            )
            for institution_account in institution_accounts
        }

    @classmethod
    def assemble_asset_accounts(
        cls,
        institutions: list[Institution],
        institution_accounts: list[InstitutionAccount],
        asset_accounts: list[AssetAccount],
    ) -> dict[str, AssetAccountDto]:
        institution_account_dtos = cls.assemble_institution_accounts(
            institutions, institution_accounts
        )
        return {
            asset_account.id: AssetAccountDto.from_domain(
                asset_account,
                institution_account_dtos[asset_account.institution_account_id],
            )
            for asset_account in asset_accounts
        }

    @classmethod
    def assemble_instruments(
        cls, instruments: list[Instrument]
    ) -> dict[str, InstrumentDto]:
        return {
            instrument.id: InstrumentDto.from_domain(instrument)
            for instrument in instruments
        }

    @classmethod
    def assemble_transactions(
        cls,
        institutions: list[Institution],
        institution_accounts: list[InstitutionAccount],
        asset_accounts: list[AssetAccount],
        instruments: list[Instrument],
        transactions: list[Transaction],
        rates_by_date: dict[date, FxRates],
        reporting_currency: str,
    ) -> list[TransactionDto]:
        asset_account_dtos = cls.assemble_asset_accounts(
            institutions,
            institution_accounts,
            asset_accounts,
        )
        instrument_dtos = cls.assemble_instruments(instruments)
        transaction_dtos: list[TransactionDto] = []
        for transaction in transactions:
            rates = rates_by_date[transaction.executed_at.date()]
            asset_account_dto = asset_account_dtos[transaction.asset_account_id]
            instrument_dto = (
                instrument_dtos[transaction.instrument_id]
                if transaction.instrument_id
                else None
            )
            transaction_dtos.append(
                TransactionDto.from_domain(
                    transaction,
                    rates,
                    reporting_currency,
                    asset_account_dto,
                    instrument_dto,
                )
            )

        return transaction_dtos

    @classmethod
    def assemble_portfolios(
        cls,
        institutions: list[Institution],
        institution_accounts: list[InstitutionAccount],
        asset_accounts: list[AssetAccount],
        instruments: list[Instrument],
        portfolios: list[Portfolio],
    ) -> list[PortfolioDto]:
        asset_account_dtos = cls.assemble_asset_accounts(
            institutions,
            institution_accounts,
            asset_accounts,
        )
        institution_account_dtos = {
            asset_account_dto.institution_account.id: asset_account_dto.institution_account
            for asset_account_dto in asset_account_dtos.values()
        }
        instrument_dtos = cls.assemble_instruments(instruments)
        portfolio_dtos: list[PortfolioDto] = []

        for portfolio in portfolios:
            account_dto: AssetAccountDto | InstitutionAccountDto | None = None
            if portfolio.scope == ConsolidationScope.ASSET_ACCOUNT:
                assert portfolio.account_id is not None
                account_dto = asset_account_dtos[portfolio.account_id]
            elif portfolio.scope == ConsolidationScope.INSTITUTION_ACCOUNT:
                assert portfolio.account_id is not None
                account_dto = institution_account_dtos[portfolio.account_id]

            portfolio_dtos.append(
                PortfolioDto.from_domain(portfolio, account_dto, instrument_dtos)
            )

        return portfolio_dtos

    @classmethod
    def assemble_portfolio_valuations(
        cls,
        portfolio_valuations: dict[str | None, PortfolioValuation],
    ) -> dict[str | None, PortfolioValuationDto]:
        return {
            account_id: PortfolioValuationDto.from_domain(portfolio_valuation)
            for account_id, portfolio_valuation in portfolio_valuations.items()
        }

    @classmethod
    def assemble_valued_portfolios(
        cls,
        institutions: list[Institution],
        institution_accounts: list[InstitutionAccount],
        asset_accounts: list[AssetAccount],
        instruments: list[Instrument],
        portfolios: list[Portfolio],
        portfolio_valuations: dict[str | None, PortfolioValuation],
    ) -> list[ValuedPortfolioDto]:
        portfolio_dtos = cls.assemble_portfolios(
            institutions,
            institution_accounts,
            asset_accounts,
            instruments,
            portfolios,
        )
        portfolio_valuation_dtos = cls.assemble_portfolio_valuations(
            portfolio_valuations
        )
        return [
            ValuedPortfolioDto(
                portfolio_dto,
                portfolio_valuation_dtos.get(
                    portfolio_dto.account.id if portfolio_dto.account else None
                ),
            )
            for portfolio_dto in portfolio_dtos
        ]
