<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { watchlistApi, type WatchlistPriceItem } from '@/api/watchlist'

const items = ref<WatchlistPriceItem[]>([])
const loading = ref(false)

const newItem = ref({ asset_class: 'stock' as const, symbol: '', exchange: '', notes: '' })
const adding = ref(false)
const showForm = ref(false)

const ASSET_ICONS: Record<string, string> = {
  crypto: '💎',
  stock: '📈',
  forex: '💱',
  options: '📊',
  sports_card: '🏀',
}

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
    const res = await watchlistApi.listWithPrices()
    items.value = res.data
  } finally {
    loading.value = false
  }
}

async function addItem() {
  if (!newItem.value.symbol) return
  adding.value = true
  try {
    await watchlistApi.add({
      asset_class: newItem.value.asset_class,
      symbol: newItem.value.symbol,
      exchange: newItem.value.exchange,
      notes: newItem.value.notes,
    })
    newItem.value = { asset_class: 'stock', symbol: '', exchange: '', notes: '' }
    showForm.value = false
    await load()
  } finally {
    adding.value = false
  }
}

async function removeItem(id: number) {
  await watchlistApi.remove(id)
  await load()
}

function currencySymbol(item: WatchlistPriceItem): string {
  if (item.asset_class === 'stock') return '¥'
  if (item.asset_class === 'crypto' || item.asset_class === 'sports_card') return '$'
  if (item.asset_class === 'forex' || item.asset_class === 'options') return '$'
  return ''
}

function priceDisplay(item: WatchlistPriceItem): string {
  if (!item.raw_data?.price) return '—'
  const unit = currencySymbol(item)
  if (item.asset_class === 'crypto' || item.raw_data.price < 1) {
    return unit + item.raw_data.price.toFixed(4)
  }
  if (item.raw_data.price > 100) {
    return unit + item.raw_data.price.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
  }
  return unit + item.raw_data.price.toFixed(2)
}

function changeDisplay(item: WatchlistPriceItem): string {
  const d = item.raw_data
  if (!d?.prev_close) return ''
  const pct = ((d.price - d.prev_close) / d.prev_close) * 100
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

onMounted(load)
</script>

<template>
  <div class="watchlist-view">
    <div class="page-header">
      <h2>监控列表</h2>
      <el-button type="primary" size="small" @click="showForm = !showForm">
        {{ showForm ? '取消' : '+ 添加' }}
      </el-button>
    </div>

    <!-- Add form -->
    <div v-if="showForm" class="add-form card">
      <div class="form-row">
        <el-select v-model="newItem.asset_class" style="width: 120px">
          <el-option label="股票" value="stock" />
          <el-option label="加密货币" value="crypto" />
          <el-option label="球星卡" value="sports_card" />
        </el-select>
        <el-input v-model="newItem.symbol" placeholder="代码，如 600519 或 BTC" style="flex:1" />
      </div>
      <div class="form-row">
        <el-input v-model="newItem.exchange" placeholder="交易所 (OKX / SSE / SZSE / eBay)" style="flex:1" />
        <el-input v-model="newItem.notes" placeholder="名称备注，如 贵州茅台" style="flex:1" />
      </div>
      <el-button type="primary" :loading="adding" @click="addItem" style="width:100%">
        添加到监控
      </el-button>
    </div>

    <!-- Asset list -->
    <div v-if="loading" class="loading">
      <el-icon class="is-loading"><Loading /></el-icon>
    </div>

    <div v-else-if="items.length === 0" class="empty-state card">
      <p>暂无监控项</p>
      <p class="hint">点击右上角添加需要追踪的资产</p>
    </div>

    <div v-else class="asset-list">
      <div v-for="item in items" :key="item.id" class="asset-card card">
        <div class="asset-left">
          <span class="asset-icon">{{ ASSET_ICONS[item.asset_class] }}</span>
          <div class="asset-info">
            <span class="asset-symbol">{{ item.symbol }}</span>
            <span class="asset-name">{{ item.notes || item.exchange || item.asset_class }}</span>
          </div>
        </div>
        <div class="asset-right">
          <span class="asset-price">{{ priceDisplay(item) }}</span>
          <span
            v-if="changeDisplay(item)"
            class="asset-change"
            :class="{ positive: item.raw_data && ((item.raw_data.price - (item.raw_data.prev_close || 0)) / (item.raw_data.prev_close || 1)) >= 0 }"
          >
            {{ changeDisplay(item) }}
          </span>
        </div>
        <el-button
          class="delete-btn"
          :icon="Delete"
          circle
          size="small"
          @click="removeItem(item.id)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.watchlist-view { padding: 16px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { margin: 0; font-size: 18px; }
.add-form { padding: 16px; margin-bottom: 16px; display: flex; flex-direction: column; gap: 10px; }
.form-row { display: flex; gap: 8px; }
.loading { display: flex; justify-content: center; padding: 40px; color: var(--text-muted); }
.empty-state { text-align: center; padding: 40px; color: var(--text-muted); }
.empty-state .hint { font-size: 13px; margin-top: 8px; }
.asset-list { display: flex; flex-direction: column; gap: 8px; }
.asset-card {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  gap: 12px;
}
.asset-left { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.asset-icon { font-size: 22px; }
.asset-info { display: flex; flex-direction: column; min-width: 0; }
.asset-symbol { font-weight: 700; font-size: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.asset-name { font-size: 12px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.asset-right { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.asset-price { font-weight: 700; font-size: 15px; }
.asset-change { font-size: 12px; color: #ef4444; }
.asset-change.positive { color: #22c55e; }
.delete-btn { margin-left: 8px; opacity: 0.4; flex-shrink: 0; }
.asset-card:hover .delete-btn { opacity: 1; }
</style>
