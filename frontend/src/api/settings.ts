import { http } from './http'
import type { Settings, SettingsSaveResult, SettingsUpdate } from '@/types/settings'

export const fetchHealth = () => http.get<{ status: string }>('/health')

export const fetchSettings = () => http.get<Settings>('/settings')

export const saveSettings = (body: SettingsUpdate) =>
  http.put<SettingsSaveResult>('/settings', body)
