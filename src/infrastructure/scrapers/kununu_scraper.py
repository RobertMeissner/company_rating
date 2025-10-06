from src.domain.value_objects.company import Company


class KununuScraper:
    """

    Implements CompanyScraper

    """

    async def get(self, company_name: str) -> Company:
        return Company(name=company_name)

    async def update(self, company_name: str) -> Company:

        return Company(name=company_name)
