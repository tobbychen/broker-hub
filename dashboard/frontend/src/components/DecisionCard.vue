<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Decision } from '@/api/client'
import { decisionsApi } from '@/api/client'
import ChatPanel from './ChatPanel.vue'

const props = defineProps<{ decision: Decision }>()
const emit = defineEmits<{ resolved: [] }>()

const loading = ref(false)
const showChat = ref(false)

const confidenceColor = computed(() => {
  const c = props.decision.confidence
  if (c >= 0.8) return 'var(--accent-green)'
  if (c >= 0.6) return 'var(--accent-yellow)'
  return 'var(--accent-red)'
})

const riskColor = computed(() => {
  const r = props.decision.risk_level
  if (r === 'low') return 'var(--accent-green)'
  if (r === 'medium') return 'var(--accent-yellow)'
  return 'var(--accent-red)'
})

async function approve() {
  loading.value = true
  try {
    await decisionsApi.resolve(props.decision.id, true)
    emit('resolved')
  } finally {
    loading.value = false
  }
}

async function reject() {
  loading.value = true
  try {
    await decisionsApi.resolve(props.decision.id, false)
    emit('resolved')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="decision-card">
    <div class="card-header">
      <span class="signal-dot" :style="{ background: confidenceColor }"></span>
      <span class="decision-type">{{ decision.decision_type.toUpperCase() }}</span>
      <span class="asset">{{ decision.symbol }}</span>
      <span class="badge-risk" :style="{ color: riskColor }">{{ decision.risk_level }}</span>
    </div>

    <div class="card-body">
      <div class="meta-row">
        <span v-if="decision.quantity" class="meta-item">
          数量: <strong>{{ decision.quantity }}</strong>
        </span>
        <span v-if="decision.action_price" class="meta-item">
          价格: <strong>¥{{ decision.action_price }}</strong>
        </span>
        <span class="meta-item">
          置信度: <strong :style="{ color: confidenceColor }">{{ (decision.confidence * 100).toFixed(0) }}%</strong>
        </span>
      </div>
      <p class="reasoning">{{ decision.reasoning }}</p>
    </div>

    <div class="card-actions">
      <el-button class="btn-ask" @click="showChat = !showChat">追问</el-button>
      <el-button class="btn-reject" :loading="loading" @click="reject">拒绝</el-button>
      <el-button class="btn-approve" :loading="loading" @click="approve">批准</el-button>
    </div>

    <ChatPanel v-if="showChat" :decision-id="decision.id" />
  </div>
</template>

<style scoped>
.decision-card {
  background: var(--bg-card);
  border-radius: var(--radius);
  margin: 12px 16px;
  padding: 16px;
  border: 1px solid var(--border);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.signal-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.decision-type {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
  letter-spacing: 1px;
}
.asset {
  font-size: 18px;
  font-weight: 700;
  flex: 1;
}
.badge-risk {
  font-size: 12px;
  font-weight: 600;
  text-transform: capitalize;
}
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.meta-item {
  font-size: 13px;
  color: var(--text-secondary);
}
.meta-item strong { color: var(--text-primary); }
.reasoning {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin-bottom: 16px;
}
.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
</style>
