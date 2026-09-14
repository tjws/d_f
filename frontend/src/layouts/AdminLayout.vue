<script setup lang="ts">
import { RouterView } from 'vue-router'
import AdminNavigation from '../components/admin/AdminNavigation.vue'
</script>

<template>
  <main class="admin-layout">
    <AdminNavigation />
    <section class="admin-content">
      <RouterView />
    </section>
  </main>
</template>

<style scoped>
.admin-layout {
  min-height: 100vh;
  background: #f8fafc;
}

.admin-content {
  max-width: 1180px;
  margin: 0 auto;
  padding: 32px 6vw 64px;
}
</style>
