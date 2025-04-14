from abc import ABC, abstractmethod
from typing import List

class BaseClient(ABC):
    @abstractmethod
    async def multiQuery(self, prefix: str, max_tokens: int, n: int, stop: str = None) -> List[str]:
        pass