from typing import Protocol

from src.domain.value_objects.company import Company


class CompanyScraperPort(Protocol):
    """Port for company scraping"""

    async def __aenter__(self): ...

    async def __aexit__(self, exc_type, exc_val, exc_tb): ...

    async def get(self, company_name: str) -> Company: ...

    async def update(self, company_name: str) -> Company: ...
