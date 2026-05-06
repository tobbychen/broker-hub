<script setup lang="ts">
import { ref, onMounted } from 'vue'

const loading = ref(false)
onMounted(() => {})
</script>

<template>
  <div class="agent-status-view">
    <div class="page-header">
      <h2>Agent 状态</h2>
    </div>
    <div class="empty-state card">
      <p>Agent 状态监控 Phase 2 实现</p>
      <small>将显示各监控器运行状态和最后检查时间</small>
    </div>
  </div>
</template>

<style scoped>
.agent-status-view { padding-top: 16px; }
.page-header { padding: 0 16px 12px; }
.page-header h2 { font-size: 20px; font-weight: 700; }
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  gap: 8px;
  color: var(--text-muted);
}
.empty-state small { font-size: 13px; }
</style>
