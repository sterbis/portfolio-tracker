from decimal import Decimal
from pathlib import Path

from portfolio_tracker.domain.shared import DualMoney, Money


def print_directory_structure() -> None:
    for root_path, dir_names, file_names in Path(
        r"src\portfolio_tracker\application"
    ).walk():
        if root_path.name.startswith("__"):
            continue

        print(root_path)
        for file_name in file_names:
            print(root_path / file_name)


price = DualMoney(
    Money(Decimal("100"), "USD"),
    Money(Decimal("2000"), "CZK"),
)
print(Decimal("3") * price)
