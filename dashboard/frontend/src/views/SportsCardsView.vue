<script setup lang="ts">
import { ref, onMounted } from 'vue'

const loading = ref(false)
onMounted(() => {})
</script>

<template>
  <div class="sports-cards-view">
    <div class="page-header">
      <h2>球星卡</h2>
    </div>
    <div class="empty-state card">
      <p>球星卡功能 Phase 2 实现</p>
      <small>将接入 Card Ladder API 显示卡牌价格和组合</small>
    </div>
  </div>
</template>

<style scoped>
.sports-cards-view { padding-top: 16px; }
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
