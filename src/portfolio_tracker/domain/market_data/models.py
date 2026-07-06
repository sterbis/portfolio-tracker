from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


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
