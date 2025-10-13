import axios from 'axios'
import type { JobListResponse, CompanyListResponse, BlacklistResponse } from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const jobsApi = {
  getJobs: async (minRating: number = 0, applyBlacklist: boolean = true): Promise<JobListResponse> => {
    const response = await api.get<JobListResponse>('/jobs', {
      params: { min_rating: minRating, apply_blacklist: applyBlacklist },
    })
    return response.data
  },

  scrapeJobs: async (): Promise<{ message: string; total: number }> => {
    const response = await api.post('/jobs/scrape')
    return response.data
  },
}

export const companiesApi = {
  getCompanies: async (): Promise<CompanyListResponse> => {
    const response = await api.get<CompanyListResponse>('/companies')
    return response.data
  },
}

export const blacklistApi = {
  getCompanyBlacklist: async (): Promise<BlacklistResponse> => {
    const response = await api.get<BlacklistResponse>('/blacklist/companies')
    return response.data
  },

  addCompanyToBlacklist: async (name: string): Promise<void> => {
    await api.post('/blacklist/companies', { name })
  },

  removeCompanyFromBlacklist: async (name: string): Promise<void> => {
    await api.delete(`/blacklist/companies/${encodeURIComponent(name)}`)
  },

  getJobBlacklist: async (): Promise<BlacklistResponse> => {
    const response = await api.get<BlacklistResponse>('/blacklist/jobs')
    return response.data
  },

  addJobToBlacklist: async (jobId: string): Promise<void> => {
    await api.post('/blacklist/jobs', { job_id: jobId })
  },

  removeJobFromBlacklist: async (jobId: string): Promise<void> => {
    await api.delete(`/blacklist/jobs/${encodeURIComponent(jobId)}`)
  },
}
