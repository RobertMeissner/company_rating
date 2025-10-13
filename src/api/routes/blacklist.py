from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import api_job_orchestrator
from src.api.models.schemas import BlacklistCompanyRequest, BlacklistJobRequest
from src.application.services.job_orchestrator import JobOrchestrator

router = APIRouter()


# Company blacklist endpoints
@router.get("/blacklist/companies")
async def get_company_blacklist(
    orchestrator: JobOrchestrator = Depends(api_job_orchestrator),
):
    blacklist = orchestrator.company_blacklist()
    return {"companies": blacklist, "total": len(blacklist)}


@router.post("/blacklist/companies")
async def add_company_to_blacklist(
    request: BlacklistCompanyRequest,
    orchestrator: JobOrchestrator = Depends(api_job_orchestrator),
):
    orchestrator.add_to_blacklist(request.name)
    orchestrator.write_company_blacklist()
    return {"message": f"Added {request.name} to blacklist"}


@router.delete("/blacklist/companies/{company_name}")
async def remove_company_from_blacklist(
    company_name: str,
    orchestrator: JobOrchestrator = Depends(api_job_orchestrator),
):
    try:
        orchestrator.remove_from_blacklist(company_name)
        orchestrator.write_company_blacklist()
        return {"message": f"Removed {company_name} from blacklist"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/blacklist/jobs")
async def get_job_blacklist(
    orchestrator: JobOrchestrator = Depends(api_job_orchestrator),
):
    blacklist = orchestrator.job_blacklist()
    return {"jobs": blacklist, "total": len(blacklist)}


@router.post("/blacklist/jobs")
async def add_job_to_blacklist(
    request: BlacklistJobRequest,
    orchestrator: JobOrchestrator = Depends(api_job_orchestrator),
):
    orchestrator.add_to_job_blacklist(request.job_id)
    orchestrator.write_job_blacklist()
    return {"message": f"Added job {request.job_id} to blacklist"}


@router.delete("/blacklist/jobs/{job_id}")
async def remove_job_from_blacklist(
    job_id: str,
    orchestrator: JobOrchestrator = Depends(api_job_orchestrator),
):
    try:
        orchestrator.remove_from_job_blacklist(job_id)
        orchestrator.write_job_blacklist()
        return {"message": f"Removed job {job_id} from blacklist"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
