<template>
  <v-container fluid class="pa-0">
    <v-row no-gutters>
      <v-col cols="12" md="3" lg="2">
        <v-card class="sidebar-card" elevation="0">
          <v-card-title class="text-h6">Filters</v-card-title>
          <v-divider></v-divider>
          <v-card-text>
            <div class="mb-6">
              <v-label class="mb-2">Minimum Rating</v-label>
              <v-slider
                v-model="minRating"
                :min="0"
                :max="5"
                :step="0.1"
                thumb-label
                color="primary"
                class="mt-4"
              >
                <template v-slot:append>
                  <v-chip color="primary" size="small">
                    {{ minRating.toFixed(1) }}
                  </v-chip>
                </template>
              </v-slider>
            </div>

            <div class="mb-6">
              <v-checkbox
                v-model="hideBlacklisted"
                label="Hide Blacklisted Jobs"
                color="primary"
                hide-details
              ></v-checkbox>
            </div>

            <v-btn
              @click="loadJobs"
              color="secondary"
              block
              prepend-icon="mdi-refresh"
            >
              Reload jobs
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="9" lg="10">
               <v-data-table
          :headers="headers"
          :items="jobs"
          :loading="loading"
          :items-per-page="25"
          item-value="job_id"
          class="elevation-1"
        >
          <template v-slot:top>
            <v-toolbar flat>
              <v-toolbar-title>
                Job Listings
                <v-chip class="ml-2" size="small" v-if="!loading">
                  {{ jobs.length }} shown, {{ ratedCount }} rated, {{ blacklistedJobIds.size }} hidden
                </v-chip>
              </v-toolbar-title>
            </v-toolbar>
          </template>

          <template v-slot:item="{ item }">
            <tr :class="{ 'bg-red-lighten-5': blacklistedJobIds.has(item.job_id) }">
              <td>
                <v-btn
                  v-if="!blacklistedJobIds.has(item.job_id)"
                  color="error"
                  size="small"
                  variant="flat"
                  @click="toggleJobVisibility(item.job_id, true)"
                >
                  Hide
                </v-btn>
                <v-btn
                  v-else
                  color="success"
                  size="small"
                  variant="flat"
                  @click="toggleJobVisibility(item.job_id, false)"
                >
                  Show
                </v-btn>
              </td>
              <td><strong>{{ item.company_name }}</strong></td>
              <td>{{ item.title }}</td>
              <td>
                <v-chip
                  v-if="item.kununu_rating"
                  color="success"
                  size="small"
                  variant="flat"
                >
                  {{ item.kununu_rating.toFixed(2) }}
                </v-chip>
                <span v-else class="text-grey">—</span>
              </td>
              <td>
                <span v-if="item.kununu_review_count">{{ item.kununu_review_count }}</span>
                <span v-else class="text-grey">—</span>
              </td>
              <td>
                <span v-if="item.location">{{ item.location }}</span>
                <span v-else class="text-grey">—</span>
              </td>
              <td>
                <v-btn
                  :href="item.url"
                  target="_blank"
                  color="secondary"
                  size="small"
                  variant="flat"
                >
                  View
                </v-btn>
              </td>
            </tr>
          </template>

          <template v-slot:loading>
            <v-progress-linear indeterminate color="primary"></v-progress-linear>
          </template>

          <template v-slot:no-data>
            <v-alert type="info" variant="tonal">
              No jobs found
            </v-alert>
          </template>
        </v-data-table>

        <v-snackbar v-model="snackbar" :timeout="3000" color="error">
          {{ errorMessage }}
        </v-snackbar>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { jobsApi, blacklistApi } from '../services/api'
import type { Job } from '../types'

const jobs = ref<Job[]>([])
const loading = ref(true)
const blacklistedJobIds = ref<Set<string>>(new Set())
const ratedCount = ref(0)
const snackbar = ref(false)
const errorMessage = ref('')

const minRating = ref(4.0)
const hideBlacklisted = ref(true)

const headers = [
  { title: 'Actions', key: 'actions', sortable: false },
  { title: 'Company', key: 'company_name', sortable: true },
  { title: 'Job Title', key: 'title', sortable: true },
  { title: 'Rating', key: 'kununu_rating', sortable: true },
  { title: 'Reviews', key: 'kununu_review_count', sortable: true },
  { title: 'Location', key: 'location', sortable: true },
  { title: 'Link', key: 'url', sortable: false },
]

const loadJobs = async () => {
  loading.value = true
  try {
    const [jobsResponse, blacklistResponse] = await Promise.all([
      jobsApi.getJobs(minRating.value, hideBlacklisted.value),
      blacklistApi.getJobBlacklist()
    ])

    jobs.value = jobsResponse.jobs
    ratedCount.value = jobsResponse.jobs.filter(j => j.kununu_rating != null).length
    blacklistedJobIds.value = new Set(blacklistResponse.jobs || [])
  } catch (err) {
    errorMessage.value = 'Failed to load jobs'
    snackbar.value = true
  } finally {
    loading.value = false
  }
}

const toggleJobVisibility = async (jobId: string, hide: boolean) => {
  try {
    if (hide) {
      blacklistedJobIds.value.add(jobId)
      await blacklistApi.addJobToBlacklist(jobId)
    } else {
      blacklistedJobIds.value.delete(jobId)
      await blacklistApi.removeJobFromBlacklist(jobId)
    }

    if (hideBlacklisted.value) {
      await loadJobs()
    }
  } catch (err) {
    errorMessage.value = 'Failed to update job visibility'
    snackbar.value = true
    await loadJobs()
  }
}

onMounted(() => {
  loadJobs()
})

watch([minRating, hideBlacklisted], () => {
  loadJobs()
})
</script>

<style scoped>
.sidebar-card {
  height: 100%;
  border-right: 1px solid rgba(0, 0, 0, 0.12);
}
</style>
