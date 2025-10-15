from datetime import datetime
from typing import Optional


class Job:
    """Job posting entity with comprehensive information from job boards."""

    job_id: str
    url: str
    company_name: str
    title: str

    # Salary information
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_interval: Optional[str] = None  # yearly, monthly, hourly

    # Location & remote
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    work_from_home_type: Optional[str] = None  # hybrid, fully_remote, etc.

    # Job details
    job_type: Optional[str] = None  # full-time, part-time, contract
    job_level: Optional[str] = None  # entry, mid, senior
    job_function: Optional[str] = None
    date_posted: Optional[datetime] = None
    description: Optional[str] = None
    skills: Optional[list[str]] = None

    # Company information
    company_industry: Optional[str] = None
    company_num_employees: Optional[str] = None
    company_revenue: Optional[str] = None
    company_description: Optional[str] = None
    company_url: Optional[str] = None

    # Legacy fields (kept for backward compatibility)
    working_model: str = ""  # deprecated, use work_from_home_type
    salary: int = 0  # deprecated, use salary_min/max

    def __init__(
        self,
        job_id: str,
        url: str,
        company_name: str,
        title: str,
        working_model: str = "",
        salary: int = 0,
        salary_min: Optional[float] = None,
        salary_max: Optional[float] = None,
        salary_currency: Optional[str] = None,
        salary_interval: Optional[str] = None,
        location: Optional[str] = None,
        is_remote: Optional[bool] = None,
        work_from_home_type: Optional[str] = None,
        job_type: Optional[str] = None,
        job_level: Optional[str] = None,
        job_function: Optional[str] = None,
        date_posted: Optional[datetime] = None,
        description: Optional[str] = None,
        skills: Optional[list[str]] = None,
        company_industry: Optional[str] = None,
        company_num_employees: Optional[str] = None,
        company_revenue: Optional[str] = None,
        company_description: Optional[str] = None,
        company_url: Optional[str] = None,
    ):
        self.job_id = job_id
        self.url = url
        self.company_name = company_name
        self.title = title
        self.working_model = working_model
        self.salary = salary
        self.salary_min = salary_min
        self.salary_max = salary_max
        self.salary_currency = salary_currency
        self.salary_interval = salary_interval
        self.location = location
        self.is_remote = is_remote
        self.work_from_home_type = work_from_home_type
        self.job_type = job_type
        self.job_level = job_level
        self.job_function = job_function
        self.date_posted = date_posted
        self.description = description
        self.skills = skills if skills is not None else []
        self.company_industry = company_industry
        self.company_num_employees = company_num_employees
        self.company_revenue = company_revenue
        self.company_description = company_description
        self.company_url = company_url
