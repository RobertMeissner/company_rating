from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, Query

from src.api.dependencies import api_job_orchestrator
from src.api.models.schemas import JobListResponse, JobResponse
from src.application.services.job_orchestrator import JobOrchestrator
from src.utils.utils import nan_to_none

router = APIRouter()


@router.get("/jobs", response_model=JobListResponse)
async def get_jobs(
    min_rating: Optional[float] = Query(default=0.0, ge=0.0, le=5.0),
    apply_blacklist: bool = Query(default=True),
    orchestrator: JobOrchestrator = Depends(api_job_orchestrator),
):
    df = orchestrator.get_jobs_dataframe(
        min_rating=min_rating, apply_blacklist=apply_blacklist
    )

    jobs = []
    for _, row in df.iterrows():
        jobs.append(
            JobResponse(
                job_id=row.get("job_id", ""),
                url=row.get("url", ""),
                company_name=row.get("company_name", ""),
                working_model=row.get("working_model", ""),
                salary=int(row.get("salary", 0) or 0),
                title=row.get("title", ""),
                kununu_rating=nan_to_none(row.get("kununu_rating")),
                kununu_review_count=(
                    int(row.get("kununu_review_count"))
                    if pd.notna(row.get("kununu_review_count"))
                    else None
                ),
                glassdoor_rating=nan_to_none(row.get("glassdoor_rating")),
                glassdoor_review_count=(
                    int(row.get("glassdoor_review_count"))
                    if pd.notna(row.get("glassdoor_review_count"))
                    else None
                ),
                location=nan_to_none(row.get("location")),
            )
        )

    return JobListResponse(jobs=jobs, total=len(jobs))


@router.post("/jobs/scrape")
async def scrape_jobs(orchestrator: JobOrchestrator = Depends(api_job_orchestrator)):
    jobs = orchestrator.scrape_jobs()
    orchestrator.deduplicate_jobs()
    orchestrator.filter_blacklisted_jobs()
    orchestrator.write()
    return {"message": f"Scraped {len(jobs)} jobs", "total": len(jobs)}
