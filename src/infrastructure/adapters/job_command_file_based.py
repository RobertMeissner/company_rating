import json
from dataclasses import asdict

from src.domain.entities.job import Job
from src.models.job_dict import JobDict
from src.utils.settings import DATA_FOLDER, JOB_FILENAME


class JobCommandFileBasedAdapter:
    """

    Implements JobCommandPort.

    File based, for PoC
    """

    filepath = f"{DATA_FOLDER}/{JOB_FILENAME}"

    def __init__(self):
        pass

    def write(self, jobs: list[Job]):
        with open(self.filepath, "w", encoding="utf-8") as f:
            for job in jobs:
                job_dict = JobDict(
                    job_id=job.job_id,
                    url=job.url,
                    company_name=job.company_name,
                    working_model=job.working_model,
                    salary=job.salary,
                    title=job.title,
                )
                f.write(json.dumps(asdict(job_dict), ensure_ascii=False) + "\n")
