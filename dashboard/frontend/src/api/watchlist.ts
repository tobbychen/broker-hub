import api from './client'

export interface WatchlistItem {
  id: number
  asset_class: 'stock' | 'crypto' | 'forex' | 'options' | 'sports_card'
  symbol: string
  exchange: string
  notes: string
  created_at?: string
}

export interface WatchlistPriceItem extends WatchlistItem {
  raw_data: { price: number; prev_close?: number; last_recorded?: number } | null
  fetched_at: string | null
}

export const watchlistApi = {
  list: () => api.get<WatchlistItem[]>('/watchlist/'),
  listWithPrices: () => api.get<WatchlistPriceItem[]>('/watchlist/prices'),
  add: (item: Omit<WatchlistItem, 'id' | 'created_at'>) =>
    api.post<{ id: number; added: boolean }>('/watchlist/', item),
  remove: (id: number) =>
    api.delete<{ deleted: boolean }>(`/watchlist/${id}`),
}
