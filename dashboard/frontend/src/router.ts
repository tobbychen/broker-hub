import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/decisions',
    },
    {
      path: '/portfolio',
      name: 'portfolio',
      component: () => import('./views/PortfolioView.vue'),
    },
    {
      path: '/decisions',
      name: 'decisions',
      component: () => import('./views/DecisionsView.vue'),
    },
    {
      path: '/daily-report',
      name: 'daily-report',
      component: () => import('./views/DailyReportView.vue'),
    },
    {
      path: '/sports-cards',
      name: 'sports-cards',
      component: () => import('./views/SportsCardsView.vue'),
    },
    {
      path: '/agent-status',
      name: 'agent-status',
      component: () => import('./views/AgentStatusView.vue'),
    },
  ],
})

export default router
