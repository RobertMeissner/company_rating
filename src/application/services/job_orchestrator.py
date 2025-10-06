from src.domain.entities.job import Job
from src.domain.ports.company_query_port import CompanyQueryPort
from src.domain.ports.job_query_port import JobQueryPort
from src.domain.value_objects.company import Company


class JobOrchestrator:

    def __init__(
        self, job_query_port: JobQueryPort, company_query_port: CompanyQueryPort
    ):
        self._job_query_port = job_query_port()
        self._company_query_port = company_query_port()

    def jobs(self) -> list[Job]:
        return self._job_query_port.get()

    def companies(self) -> list[Company]:
        return self._company_query_port.get()
