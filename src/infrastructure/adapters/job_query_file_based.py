import pandas as pd

from src.domain.entities.job import Job
from src.utils.settings import DATA_FOLDER


class JobQueryFileBasedAdapter:
    """

    Implements JobQueryPort.

    File based, for PoC
    """

    def __init__(self):
        pass

    def get(self) -> list[Job]:
        df = pd.read_csv(f"{DATA_FOLDER}/jobs.csv")
        jobs = []
        for index, row in df.iterrows():
            # Prefer job_url_direct, fall back to job_url if not available
            url = (
                row.get("job_url_direct")
                if pd.notna(row.get("job_url_direct"))
                else row.get("job_url", "")
            )

            job = Job(
                job_id=row["id"],
                url=url,
                title=row["title"],
                salary=0,
                company_name=row["company"],
                working_model=row["is_remote"],
            )
            jobs.append(job)

        return jobs
