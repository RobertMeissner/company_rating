import json

import pandas as pd

from src.domain.value_objects.company import Company
from src.utils.settings import COMPANY_FILENAME, DATA_FOLDER


class CompanyQueryFileBasedAdapter:
    """

    Implements CompanyQueryPort.

    File based, for PoC
    """

    filepath = f"{DATA_FOLDER}/{COMPANY_FILENAME}"

    def __init__(self):
        pass

    def _raw_companies(self) -> list[Company]:
        df = pd.read_csv(f"{DATA_FOLDER}/output.csv")
        companies = []
        for index, row in df.iterrows():
            company = Company(
                name=row["company_name"],
                location="",
                kununu_rating=row["rating"],
                glassdoor_rating=0,
                alternative_names=[],
            )
            companies.append(company)
        return companies

    def _companies(self) -> list[Company]:
        companies = []
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    companies.append(Company(**json.loads(line)))
        return companies

    def get(self, load_raw: bool = False) -> list[Company]:

        companies = self._companies()

        if load_raw:
            company_names = {company.name for company in companies}
            raw_companies = self._raw_companies()
            for raw_company in raw_companies:
                if raw_company.name not in company_names:
                    companies.append(raw_company)

        return companies
