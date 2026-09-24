from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class ProviderMetadata:
    id: str
    name: str
    supported_countries: set[str]
    requires_kyc: bool
    requires_capital: bool
    automation_allowed: bool
    official_api_available: bool
    minimum_withdrawal_usd: float

class IncomeProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        raise NotImplementedError

    @abstractmethod
    async def discover(self) -> Sequence[dict]:
        raise NotImplementedError
