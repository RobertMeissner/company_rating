import json
from dataclasses import asdict

from src.domain.value_objects.company import Company
from src.utils.settings import COMPANY_FILENAME, DATA_FOLDER


class CompanyCommandFileBasedAdapter:
    """

    Implements CompanyCommandPort.

    File based, for PoC
    """

    filepath = f"{DATA_FOLDER}/{COMPANY_FILENAME}"

    def __init__(self):
        pass

    def write(self, companies: list[Company]):
        with open(self.filepath, "w", encoding="utf-8") as f:
            for company in companies:
                f.write(json.dumps(asdict(company), ensure_ascii=False) + "\n")
