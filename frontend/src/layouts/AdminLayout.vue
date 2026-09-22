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
  background:
    radial-gradient(circle at 100% 0, rgb(37 99 235 / 8%), transparent 27rem),
    linear-gradient(180deg, #eef5ff 0, #f8fbff 320px);
}

.admin-content {
  max-width: 1240px;
  margin: 0 auto;
  padding: 36px 6vw 72px;
}
@media (max-width: 700px) { .admin-content { padding: 26px 18px 52px; } }
</style>
