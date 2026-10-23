from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType

from portfolio_tracker.domain.fx import FxRates
from portfolio_tracker.domain.shared import Money


@dataclass(frozen=True, kw_only=True)
class MarketPrices:
    as_of: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc), compare=False
    )
    prices: MappingProxyType[str, Money]


@dataclass(frozen=True, kw_only=True)
class MarketData:
    as_of: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc), compare=False
    )
    prices: MarketPrices
    rates: FxRates

    def merge(self, other: MarketData) -> MarketData:
        if self.rates.base_currency != other.rates.base_currency:
            raise ValueError(
                f"Currency mismatch. Expected {self.rates.base_currency}, got {other.rates.base_currency}."
            )
        
        return MarketData(
            as_of=other.as_of,
            prices=MarketPrices(
                as_of=other.prices.as_of,
                prices=MappingProxyType(self.prices.prices | other.prices.prices),
            ),
            rates=FxRates(
                effective_on=other.rates.effective_on,
                base_currency=self.rates.base_currency,
                rates=MappingProxyType(self.rates.rates | other.rates.rates),
            ),
        )


@dataclass(frozen=True)
class StockSplits:
    instrument_id: str
    splits: dict[datetime, Decimal]

    def get_multiplier(self, from_datetime: datetime, to_datetime: datetime) -> Decimal:
        multiplier = Decimal("1.0")

        for split_datetime, ratio in self.splits.items():
            if from_datetime < split_datetime <= to_datetime:
                multiplier *= ratio

        return multiplier
