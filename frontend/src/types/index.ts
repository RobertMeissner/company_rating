export interface Job {
  job_id: string
  url: string
  company_name: string
  working_model: string
  salary: number
  title: string
  kununu_rating?: number | null
  kununu_review_count?: number | null
  glassdoor_rating?: number | null
  glassdoor_review_count?: number | null
  location?: string | null
}

export interface Company {
  name: string
  location?: string | null
  kununu_rating?: number | null
  kununu_review_count?: number | null
  glassdoor_rating?: number | null
  glassdoor_review_count?: number | null
  website?: string | null
  url?: string | null
}

export interface JobListResponse {
  jobs: Job[]
  total: number
}

export interface CompanyListResponse {
  companies: Company[]
  total: number
}

export interface BlacklistResponse {
  companies?: string[]
  jobs?: string[]
  total: number
}
