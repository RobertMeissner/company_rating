from typing import Protocol

from src.domain.value_objects.company import Company


class CompanyScraperPort(Protocol):
    """Port for company scraping"""

    async def get(self, company: Company) -> Company: ...

    async def update(self, company: Company) -> Company: ...
