from typing import Protocol

from src.domain.value_objects.company import Company


class CompanyScraper(Protocol):
    """Port for Job scraping"""

    async def get(self, company_name: str) -> Company: ...

    async def update(self, company_name: str) -> Company: ...
