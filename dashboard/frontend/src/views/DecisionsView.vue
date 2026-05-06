<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { decisionsApi, type Decision } from '@/api/client'
import DecisionCard from '@/components/DecisionCard.vue'

const decisions = ref<Decision[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await decisionsApi.getPending()
    decisions.value = res.data
  } finally {
    loading.value = false
  }
}

let timer: number
onMounted(() => { load(); timer = window.setInterval(load, 30000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="decisions-view">
    <div class="page-header">
      <h2>待决策</h2>
      <span class="count-badge" v-if="decisions.length">{{ decisions.length }}</span>
    </div>

    <div v-if="loading && !decisions.length" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <div v-else-if="!decisions.length" class="empty-state">
      <el-icon :size="48" color="var(--text-muted)"><SuccessFilled /></el-icon>
      <p>暂无待决策项</p>
      <small>Agent 会在发现机会时提醒你</small>
    </div>

    <DecisionCard v-for="d in decisions" :key="d.id" :decision="d" @resolved="load" />
  </div>
</template>

<style scoped>
.decisions-view { padding-top: 16px; }
.page-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px 8px;
}
.page-header h2 { font-size: 20px; font-weight: 700; }
.count-badge {
  background: var(--accent);
  color: white;
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 13px;
  font-weight: 700;
}
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--text-muted);
}
.empty-state small { font-size: 13px; }
</style>
