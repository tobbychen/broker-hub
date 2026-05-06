<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dailyReportApi, type DailyReport } from '@/api/client'

const report = ref<DailyReport | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await dailyReportApi.getLatest()
    report.value = res.data
  } catch {
    report.value = null
  } finally {
    loading.value = false
  }
}

function parseList(text: string): string[] {
  if (!text) return []
  return text.split('\n').filter(l => l.trim())
}

onMounted(load)
</script>

<template>
  <div class="daily-report-view">
    <div class="page-header">
      <h2>早间简报</h2>
      <span class="date">{{ new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }) }}</span>
    </div>

    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <div v-else-if="!report" class="empty-state card">
      <p>暂无今日简报</p>
      <small>简报将于每日 08:00 自动生成</small>
    </div>

    <template v-else>
      <div class="report-section card">
        <div class="section-title">🌙 隔夜行情</div>
        <ul class="bullet-list">
          <li v-for="item in parseList(report.overnight_summary)" :key="item">{{ item }}</li>
        </ul>
      </div>

      <div class="report-section card">
        <div class="section-title accent">⚠️ 重要事件</div>
        <ul class="bullet-list">
          <li v-for="item in parseList(report.critical_events)" :key="item">{{ item }}</li>
        </ul>
      </div>

      <div class="report-section card">
        <div class="section-title highlight">🎯 投资窗口</div>
        <ul class="bullet-list">
          <li v-for="item in parseList(report.investment_windows)" :key="item">{{ item }}</li>
        </ul>
      </div>
    </template>
  </div>
</template>

<style scoped>
.daily-report-view { padding-top: 16px; }
.page-header { padding: 0 16px 12px; }
.page-header h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.page-header .date { font-size: 13px; color: var(--text-muted); }
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  gap: 8px;
  color: var(--text-muted);
}
.empty-state small { font-size: 13px; }
.report-section { margin-bottom: 8px; }
.section-title { font-size: 14px; font-weight: 700; margin-bottom: 10px; }
.section-title.accent { color: var(--accent-yellow); }
.section-title.highlight { color: var(--accent-green); }
.bullet-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.bullet-list li {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-secondary);
  padding-left: 16px;
  position: relative;
}
.bullet-list li::before { content: '•'; position: absolute; left: 0; color: var(--text-muted); }
</style>
