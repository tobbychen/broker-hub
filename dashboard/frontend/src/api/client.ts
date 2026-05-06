import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export default api

export interface PortfolioSummary {
  total_value: number
  allocation: Record<string, { cost: number; pct: number }>
  by_class: Array<{ asset_class: string; position_count: number; total_cost: number }>
}

export interface Position {
  id: number
  asset_class: string
  symbol: string
  exchange: string
  quantity: number
  avg_cost: number
  currency: string
  notes: string
  created_at: string
  updated_at: string
}

export interface Decision {
  id: number
  decision_type: string
  asset_class: string
  symbol: string
  exchange: string
  quantity: number | null
  action_price: number | null
  confidence: number
  reasoning: string
  risk_level: string
  status: string
  timeout_at: string | null
  created_at: string
}

export interface DailyReport {
  report_date: string
  overnight_summary: string
  critical_events: string
  investment_windows: string
  risk_metrics: string
  generated_at: string
}

export interface ChatMessage {
  role: 'human' | 'agent'
  content: string
  created_at?: string
}

export const portfolioApi = {
  getSummary: () => api.get<PortfolioSummary>('/portfolio/summary'),
  getPositions: () => api.get<Position[]>('/portfolio/positions'),
}

export const decisionsApi = {
  getPending: () => api.get<Decision[]>('/decisions/pending'),
  resolve: (id: number, approved: boolean) =>
    api.post(`/decisions/${id}/resolve`, { approved }),
}

export const dailyReportApi = {
  getLatest: () => api.get<DailyReport>('/daily-report/latest'),
}

export const chatApi = {
  getHistory: (decisionId: number) =>
    api.get<ChatMessage[]>(`/chat/${decisionId}`),
  send: (decisionId: number, message: string) =>
    api.post('/chat/send', { decision_id: decisionId, message }),
}
