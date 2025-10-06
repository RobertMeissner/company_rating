from src.domain.entities.job import Job
from src.domain.ports.company_command_port import CompanyCommandPort
from src.domain.ports.company_query_port import CompanyQueryPort
from src.domain.ports.job_query_port import JobQueryPort
from src.domain.value_objects.company import Company


class JobOrchestrator:
    _companies: list[Company] = []

    def __init__(
        self,
        job_query_port: JobQueryPort,
        company_query_port: CompanyQueryPort,
        company_command_port: CompanyCommandPort,
    ):
        self._job_query_port = job_query_port
        self._company_query_port = company_query_port
        self._company_command_port = company_command_port

    def jobs(self) -> list[Job]:
        return self._job_query_port.get()

    def companies(self) -> list[Company]:
        if not self._companies:
            self._companies = self._company_query_port.get()
        return self._companies

    def write(self):
        self._company_command_port.write(self.companies())

    def sort_companies(self):
        self._companies.sort(key=lambda c: c.name.lower())

    def deduplicate_companies(self):
        deduplicated_companies = []
        seen_names = set()

        for company in self.companies():
            name_key = company.name.lower()

            if name_key not in seen_names:
                seen_names.add(name_key)
                deduplicated_companies.append(company)

        print(f"Before #companies: {len(self.companies())}")
        print(f"After deduplication #companies: {len(deduplicated_companies)}")
        self._companies = deduplicated_companies
