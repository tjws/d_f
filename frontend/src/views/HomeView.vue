<script setup lang="ts">
import { RouterLink } from 'vue-router'

const projectName = '擎天学智 K12 智能销售辅助系统'

const entryPoints = [
  { to: '/customers', label: '客户工作台', description: '查看客户、学生、画像与完整跟进记录', icon: '◌' },
  { to: '/my-work', label: '我的待办', description: '按优先级处理日程、提醒和需要跟进的客户', icon: '✓' },
  { to: '/pending-actions', label: '人工确认队列', description: '确认、编辑或拒绝 AI 生成的建议草稿', icon: '✦' },
  { to: '/sidebar', label: '会话侧边栏模拟', description: '在本地模拟企业微信会话与人工发送流程', icon: '↗' },
]
</script>

<template>
  <main class="home-page">
    <section class="hero-card">
      <div class="hero-copy">
        <p class="eyebrow">K12 Sales Assistant</p>
        <h1>{{ projectName }}</h1>
        <p class="subtitle">把客户事实、销售跟进与 AI 草稿放在同一处；每一项对外动作始终由人工确认。</p>
        <div class="hero-actions">
          <RouterLink class="primary-link" to="/customers">进入客户工作台</RouterLink>
          <RouterLink class="secondary-link" to="/pending-actions">查看待处理建议</RouterLink>
        </div>
      </div>
      <aside class="principle-card">
        <span class="principle-icon">✦</span>
        <strong>人工在环</strong>
        <p>AI 负责整理与建议，不会自动向家长发送消息或自动修改业务结果。</p>
      </aside>
    </section>

    <section class="entry-section" aria-label="常用入口">
      <div class="section-heading"><div><p class="eyebrow">Start Here</p><h2>今天从哪里开始</h2></div><p>按工作流进入，而不是在功能清单里寻找。</p></div>
      <div class="entry-grid">
        <RouterLink v-for="item in entryPoints" :key="item.to" :to="item.to" class="entry-card">
          <span class="entry-icon">{{ item.icon }}</span>
          <div><h3>{{ item.label }}</h3><p>{{ item.description }}</p></div>
          <span class="entry-arrow">→</span>
        </RouterLink>
      </div>
    </section>
  </main>
</template>

<style scoped>
.home-page { min-height: calc(100vh - 64px); padding: clamp(28px, 6vw, 76px) clamp(18px, 7vw, 110px); }
.hero-card { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: clamp(24px, 5vw, 72px); max-width: 1240px; margin: 0 auto; padding: clamp(28px, 5vw, 58px); overflow: hidden; border: 1px solid rgb(255 255 255 / 72%); border-radius: 28px; background: linear-gradient(135deg, #173fa4, #2563eb 52%, #4f46e5); box-shadow: var(--shadow-float); position: relative; }.hero-card::after { position: absolute; width: 340px; height: 340px; border: 1px solid rgb(255 255 255 / 14%); border-radius: 50%; right: -150px; top: -178px; content: ''; }.hero-copy { position: relative; z-index: 1; color: white; }.eyebrow { margin: 0 0 10px; color: #bfdbfe; font-size: 12px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }.hero-copy h1 { max-width: 700px; margin: 0; color: white; font-size: clamp(34px, 5vw, 58px); line-height: 1.13; }.subtitle { max-width: 680px; margin: 18px 0 0; color: #dbeafe; font-size: 17px; line-height: 1.7; }.hero-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 28px; }.primary-link, .secondary-link { padding: 11px 16px; border-radius: 10px; font-weight: 800; text-decoration: none; }.primary-link { color: #173fa4; background: white; }.secondary-link { border: 1px solid rgb(255 255 255 / 35%); color: white; background: rgb(15 23 42 / 16%); }.principle-card { align-self: end; position: relative; z-index: 1; padding: 22px; border: 1px solid rgb(255 255 255 / 22%); border-radius: 18px; color: white; background: rgb(15 23 42 / 18%); backdrop-filter: blur(10px); }.principle-icon { display: grid; width: 34px; height: 34px; margin-bottom: 16px; place-items: center; border-radius: 11px; color: #1d4ed8; background: #dbeafe; }.principle-card strong { font-size: 18px; }.principle-card p { margin: 8px 0 0; color: #dbeafe; font-size: 13px; line-height: 1.65; }
.entry-section { max-width: 1240px; margin: 44px auto 0; }.section-heading { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 16px; }.section-heading .eyebrow { color: var(--brand); }.section-heading h2 { margin: 0; font-size: 25px; }.section-heading > p { margin: 0; color: var(--muted); }.entry-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }.entry-card { display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; gap: 14px; align-items: center; padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-md); color: inherit; background: rgb(255 255 255 / 84%); box-shadow: var(--shadow-sm); text-decoration: none; transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease; }.entry-card:hover { transform: translateY(-2px); border-color: #a9c6fa; box-shadow: var(--shadow-card); }.entry-icon { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 13px; color: var(--brand); background: var(--brand-soft); font-size: 20px; font-weight: 800; }.entry-card h3 { margin: 0 0 5px; font-size: 17px; }.entry-card p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.55; }.entry-arrow { color: var(--brand); font-size: 20px; }
@media (max-width: 760px) { .hero-card { grid-template-columns: 1fr; }.principle-card { max-width: 360px; }.entry-grid { grid-template-columns: 1fr; }.section-heading { align-items: flex-start; flex-direction: column; } }
</style>
