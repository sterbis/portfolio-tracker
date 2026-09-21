from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateAssetAccountCommand:
    account_id: str
    external_id: str
    name: str
