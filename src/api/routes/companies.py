import pandas as pd
from fastapi import APIRouter, Depends

from src.api.dependencies import api_job_orchestrator
from src.api.models.schemas import CompanyListResponse, CompanyResponse
from src.application.services.job_orchestrator import JobOrchestrator
from src.utils.utils import nan_to_none

router = APIRouter()


@router.get("/companies", response_model=CompanyListResponse)
async def get_companies(orchestrator: JobOrchestrator = Depends(api_job_orchestrator)):

    company_responses = []
    for company in orchestrator.companies():
        company_responses.append(
            CompanyResponse(
                name=company.name,
                location=nan_to_none(company.location),
                kununu_rating=nan_to_none(company.kununu_rating),
                kununu_review_count=(
                    int(company.kununu_review_count)
                    if pd.notna(company.kununu_review_count)
                    else None
                ),
                glassdoor_rating=nan_to_none(company.glassdoor_rating),
                glassdoor_review_count=(
                    int(company.glassdoor_review_count)
                    if pd.notna(company.glassdoor_review_count)
                    else None
                ),
                website=nan_to_none(company.website),
                url=nan_to_none(company.url),
            )
        )

    return CompanyListResponse(
        companies=company_responses, total=len(company_responses)
    )
