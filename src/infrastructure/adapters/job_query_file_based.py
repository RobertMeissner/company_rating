import json
from enum import Enum
from pathlib import Path

import pandas as pd

from src.domain.entities.job import Job
from src.utils.logger import get_logger
from src.utils.settings import DATA_FOLDER, JOB_FILENAME
from src.utils.utils import ensure_file_exists

logger = get_logger(__name__)


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
        ensure_file_exists(f"{DATA_FOLDER}/{JOB_FILENAME}")

    def get(self) -> list[Job]:
        match self._filetype:
            case FileType.CSV:
                jobs = self._read_csv()
            case FileType.JSONL:
                jobs = self._read_jsonl()
            case _:
                jobs = []
        return jobs

    def _read_csv(self) -> list[Job]:
        filepath = f"{DATA_FOLDER}/jobs.csv"
        jobs = []

        # CSV files are not auto-created, only JSONL files
        if not Path(filepath).exists():
            logger.warning(
                f"Jobs CSV file not found: {filepath}. Starting with empty list."
            )
            return jobs

        df = pd.read_csv(filepath)
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
