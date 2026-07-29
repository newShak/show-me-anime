import { http } from './http'
import type { Settings } from '@/types/settings'

export const fetchHealth = () => http.get<{ status: string }>('/health')

export const fetchSettings = () => http.get<Settings>('/settings')
