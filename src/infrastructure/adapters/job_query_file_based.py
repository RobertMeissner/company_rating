import json
from enum import Enum
from unittest import case

import pandas as pd

from src.domain.entities.job import Job
from src.utils.settings import DATA_FOLDER, JOB_FILENAME


class FileType(Enum):
    CSV = "csv"
    JSONL = "jsonl"


class JobQueryFileBasedAdapter:
    """

    Implements JobQueryPort.

    File based, for PoC
    """

    def __init__(self):
        self._filetype = FileType.JSONL

    def get(self) -> list[Job]:
        print(self._filetype)
        match self._filetype:
            case FileType.CSV:
                jobs = self._read_csv()
            case FileType.JSONL:
                jobs = self._read_jsonl()
            case _:
                jobs = []
        return jobs

    def _read_csv(self) -> list[Job]:
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

    def _read_jsonl(self) -> list[Job]:
        filepath = f"{DATA_FOLDER}/{JOB_FILENAME}"
        jobs = []

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue

                job_data = json.loads(line)
                job = Job(
                    job_id=job_data["job_id"],
                    url=job_data["url"],
                    company_name=job_data["company_name"],
                    working_model=job_data["working_model"],
                    salary=job_data["salary"],
                    title=job_data["title"],
                )
                jobs.append(job)

        return jobs
