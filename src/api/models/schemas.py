from typing import Optional

from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: str
    url: str
    company_name: str
    working_model: str
    salary: int
    title: str
    kununu_rating: Optional[float] = None
    kununu_review_count: Optional[int] = None
    glassdoor_rating: Optional[float] = None
    glassdoor_review_count: Optional[int] = None
    location: Optional[str] = None


class CompanyResponse(BaseModel):
    name: str
    location: Optional[str] = None
    kununu_rating: Optional[float] = None
    kununu_review_count: Optional[int] = None
    glassdoor_rating: Optional[float] = None
    glassdoor_review_count: Optional[int] = None
    website: Optional[str] = None
    url: Optional[str] = None


# Request models
class BlacklistCompanyRequest(BaseModel):
    name: str


class BlacklistJobRequest(BaseModel):
    job_id: str


class JobFilterParams(BaseModel):
    min_rating: float = 0.0
    apply_blacklist: bool = True


# Response wrappers
class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class CompanyListResponse(BaseModel):
    companies: list[CompanyResponse]
    total: int
