<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { portfolioApi, type PortfolioSummary, type Position } from '@/api/client'

const summary = ref<PortfolioSummary | null>(null)
const positions = ref<Position[]>([])
const loading = ref(false)

const ASSET_COLORS: Record<string, string> = {
  crypto: '#f7931a',
  stock: '#2196f3',
  forex: '#4caf50',
  options: '#9c27b0',
  sports_card: '#ff5722',
}

async function load() {
  loading.value = true
  try {
    const [sumRes, posRes] = await Promise.all([
      portfolioApi.getSummary(),
      portfolioApi.getPositions(),
    ])
    summary.value = sumRes.data
    positions.value = posRes.data
  } finally {
    loading.value = false
  }
}

const pieData = computed(() => {
  if (!summary.value?.allocation) return []
  return Object.entries(summary.value.allocation).map(([name, info]) => ({
    name,
    value: info.cost,
    itemStyle: { color: ASSET_COLORS[name] || '#888' },
  }))
})

onMounted(load)
</script>

<template>
  <div class="portfolio-view">
    <div class="total-value-card card">
      <div class="label">总资产</div>
      <div class="value">
        ¥{{ summary?.total_value?.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) ?? '—' }}
      </div>
    </div>

    <div class="card allocation-card" v-if="summary?.allocation">
      <div class="allocation-legend">
        <div v-for="(info, name) in summary.allocation" :key="name" class="legend-item">
          <span class="dot" :style="{ background: ASSET_COLORS[name as string] || '#888' }"></span>
          <span class="name">{{ name }}</span>
          <span class="pct">{{ info.pct }}%</span>
          <span class="cost">¥{{ info.cost.toLocaleString('zh-CN') }}</span>
        </div>
      </div>
    </div>

    <div class="positions-list">
      <div v-for="pos in positions" :key="pos.id" class="position-row card">
        <div class="pos-main">
          <span class="pos-symbol">{{ pos.symbol }}</span>
          <span class="pos-exchange">{{ pos.exchange || pos.asset_class }}</span>
        </div>
        <div class="pos-value">
          <span class="qty">{{ pos.quantity }} 股/个</span>
          <span class="cost">¥{{ (pos.quantity * pos.avg_cost).toLocaleString('zh-CN') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.total-value-card { text-align: center; padding: 24px 16px; }
.total-value-card .label { font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; }
.total-value-card .value { font-size: 32px; font-weight: 800; }
.allocation-card { padding: 12px 16px; }
.allocation-legend { display: flex; flex-direction: column; gap: 8px; }
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.legend-item .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.legend-item .name { flex: 1; text-transform: capitalize; }
.legend-item .pct { color: var(--text-secondary); width: 40px; text-align: right; }
.legend-item .cost { font-weight: 600; width: 80px; text-align: right; }
.position-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin: 8px 16px;
}
.pos-main { display: flex; flex-direction: column; gap: 2px; }
.pos-symbol { font-weight: 700; font-size: 15px; }
.pos-exchange { font-size: 12px; color: var(--text-muted); text-transform: capitalize; }
.pos-value { text-align: right; display: flex; flex-direction: column; gap: 2px; }
.pos-value .qty { font-size: 12px; color: var(--text-secondary); }
.pos-value .cost { font-weight: 600; font-size: 15px; }
</style>
