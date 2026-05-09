<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/watchlist', label: '监控', icon: 'Watch' },
  { path: '/decisions', label: '决策', icon: 'Operation' },
  { path: '/daily-report', label: '日报', icon: 'Document' },
  { path: '/portfolio', label: '持仓', icon: 'Wallet' },
  { path: '/agent-status', label: '状态', icon: 'Monitor' },
]
</script>

<template>
  <nav class="bottom-nav">
    <router-link
      v-for="item in navItems"
      :key="item.path"
      :to="item.path"
      class="nav-item"
      :class="{ active: route.path === item.path }"
    >
      <el-icon :size="22">
        <component :is="item.icon" />
      </el-icon>
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped>
.bottom-nav {
  display: flex;
  justify-content: space-around;
  align-items: center;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border);
  padding: 8px 0;
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
  flex-shrink: 0;
}
.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 8px;
  transition: color 0.2s;
}
.nav-item.active { color: var(--accent); }
</style>
