<template>
  <v-app>
    <v-app-bar color="primary" prominent>
      <v-toolbar-title class="text-h5">
        Company Rating Dashboard
      </v-toolbar-title>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <v-card>
          <v-tabs v-model="activeTab" bg-color="primary">
            <v-tab value="jobs">
              <v-icon start>mdi-briefcase</v-icon>
              Jobs
            </v-tab>
            <v-tab value="companies">
              <v-icon start>mdi-domain</v-icon>
              Companies
            </v-tab>
          </v-tabs>

          <v-card-text class="pa-4">
            <JobList v-if="activeTab === 'jobs'" />
            <CompanyList v-else />
          </v-card-text>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import JobList from './components/JobList.vue'
import CompanyList from './components/CompanyList.vue'

const activeTab = ref('jobs')
</script>
