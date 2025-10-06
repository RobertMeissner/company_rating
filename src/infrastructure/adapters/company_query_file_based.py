import pandas as pd

from src.domain.value_objects.company import Company
from src.utils.settings import DATA_FOLDER


class CompanyQueryFileBasedAdapter:
    """

    Implements CompanyQueryPort.

    File based, for PoC
    """

    def __init__(self):
        pass

    def get(self) -> list[Company]:
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
