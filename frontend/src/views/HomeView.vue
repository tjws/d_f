<script setup lang="ts">
const projectName = '擎天学智 K12 智能销售辅助系统'
</script>

<template>
  <!-- 首页外壳，后续会替换为真正的工作台首页 -->
  <main class="app-shell">
    <header class="app-header">
      <p class="eyebrow">K12 Sales Assistant</p>
      <h1>{{ projectName }}</h1>
      <p class="subtitle">
        AI provides suggestions. Humans make the final decision.
      </p>
    </header>

    <section class="workspace-placeholder">
      <h2>Customer Workspace</h2>
      <p>
        下一步将连接客户、客户画像、AI 回复建议、标签和日程功能。
      </p>
    </section>
  </main>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding: 64px 8vw;
  color: #1f2937;
  background: #f8fafc;
}

.app-header {
  max-width: 860px;
  margin: 0 auto 40px;
}

.eyebrow {
  margin: 0 0 12px;
  color: #2563eb;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(32px, 5vw, 56px);
  line-height: 1.15;
}

.subtitle {
  margin-top: 18px;
  color: #64748b;
  font-size: 18px;
}

.workspace-placeholder {
  max-width: 860px;
  margin: 0 auto;
  padding: 32px;
  border: 1px solid #dbeafe;
  border-radius: 20px;
  background: white;
  box-shadow: 0 12px 30px rgb(15 23 42 / 8%);
}

.workspace-placeholder h2 {
  margin-top: 0;
  color: #1d4ed8;
}
</style>