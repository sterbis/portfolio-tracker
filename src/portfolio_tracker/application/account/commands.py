from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateAssetAccountCommand:
    account_id: str
    name: str
