<template>
  <aside class="navigation">
    <p class="eyebrow">Admin Console</p>
    <h1>管理后台</h1>
    <nav>
      <RouterLink to="/admin/users">用户与组织</RouterLink>
      <RouterLink to="/admin/audit-logs">审计日志</RouterLink>
      <RouterLink to="/customers">返回客户工作台</RouterLink>
    </nav>
  </aside>
</template>

<style scoped>
.navigation {
  padding: 24px;
  color: white;
  background: #0f172a;
}

.eyebrow {
  margin: 0 0 6px;
  color: #93c5fd;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  margin: 0 0 20px;
  font-size: 24px;
}

nav {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

a {
  padding: 8px 12px;
  border-radius: 8px;
  color: #cbd5e1;
  text-decoration: none;
}

a.router-link-active {
  color: white;
  background: #2563eb;
}
</style>
