from dataclasses import dataclass


@dataclass
class JobDict:
    job_id: str
    url: str
    company_name: str
    working_model: str
    salary: int
    title: str
