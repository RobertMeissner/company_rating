<template>
  <div>
    <v-data-table
      :headers="headers"
      :items="companies"
      :loading="loading"
      :items-per-page="25"
      item-value="name"
      class="elevation-1"
    >
      <template v-slot:top>
        <v-toolbar flat>
          <v-toolbar-title>
            Companies
            <v-chip class="ml-2" size="small" v-if="!loading">
              {{ companies.length }} total, {{ ratedCount }} rated
            </v-chip>
          </v-toolbar-title>
        </v-toolbar>
      </template>

      <template v-slot:item.name="{ item }">
        <strong>{{ item.name }}</strong>
      </template>

      <template v-slot:item.kununu_rating="{ item }">
        <v-chip
          v-if="item.kununu_rating"
          color="success"
          size="small"
          variant="flat"
        >
          {{ item.kununu_rating.toFixed(2) }}
        </v-chip>
        <span v-else class="text-grey">—</span>
      </template>

      <template v-slot:item.kununu_review_count="{ item }">
        <span v-if="item.kununu_review_count">{{ item.kununu_review_count }}</span>
        <span v-else class="text-grey">—</span>
      </template>

      <template v-slot:item.location="{ item }">
        <span v-if="item.location">{{ item.location }}</span>
        <span v-else class="text-grey">—</span>
      </template>

      <template v-slot:item.website="{ item }">
        <v-btn
          v-if="item.website"
          :href="item.website"
          target="_blank"
          color="secondary"
          size="small"
          variant="flat"
        >
          Website
        </v-btn>
        <span v-else class="text-grey">—</span>
      </template>

      <template v-slot:item.url="{ item }">
        <v-btn
          v-if="item.url"
          :href="item.url"
          target="_blank"
          color="secondary"
          size="small"
          variant="flat"
        >
          View
        </v-btn>
        <span v-else class="text-grey">—</span>
      </template>

      <template v-slot:loading>
        <v-progress-linear indeterminate color="primary"></v-progress-linear>
      </template>

      <template v-slot:no-data>
        <v-alert type="info" variant="tonal">
          No companies found
        </v-alert>
      </template>
    </v-data-table>

    <v-snackbar v-model="snackbar" :timeout="3000" color="error">
      {{ errorMessage }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { companiesApi } from '../services/api'
import type { Company } from '../types'

const companies = ref<Company[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const ratedCount = ref(0)
const snackbar = ref(false)
const errorMessage = ref('')

const headers = [
  { title: 'Company Name', key: 'name', sortable: true },
  { title: 'Rating', key: 'kununu_rating', sortable: true },
  { title: 'Reviews', key: 'kununu_review_count', sortable: true },
  { title: 'Location', key: 'location', sortable: true },
  { title: 'Website', key: 'website', sortable: false },
  { title: 'Kununu', key: 'url', sortable: false },
]

const loadCompanies = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await companiesApi.getCompanies()
    companies.value = response.companies.sort((a, b) => {
      if (a.kununu_rating && b.kununu_rating) {
        return b.kununu_rating - a.kununu_rating
      }
      if (a.kununu_rating) return -1
      if (b.kununu_rating) return 1
      return a.name.localeCompare(b.name)
    })
    ratedCount.value = response.companies.filter(c => c.kununu_rating != null).length
  } catch (err) {
    error.value = 'Failed to load companies'
    errorMessage.value = 'Failed to load companies'
    snackbar.value = true
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadCompanies()
})
</script>
