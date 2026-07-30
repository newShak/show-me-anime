import { http } from './http'
import type { ScanJob } from '@/types/node'

export type ScanMode = 'incremental' | 'full'

export const triggerScan = (mode: ScanMode = 'incremental') =>
  http.post<ScanJob>('/scan/trigger', { mode })

export const fetchScanStatus = () => http.get<ScanJob | null>('/scan/status')
