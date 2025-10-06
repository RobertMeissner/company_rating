class Job:
    job_id: str
    url: str
    company_name: str
    working_model: str  # hybrid, remote?
    salary: int
    title: str

    def __init__(self, job_id, url, company_name, working_model, salary, title):
        self.job_id = job_id
        self.url = url
        self.company_name = company_name
        self.working_model = working_model
        self.salary = salary
        self.title = title
