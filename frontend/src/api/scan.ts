import { http } from './http'
import type { ScanJob } from '@/types/node'

export const triggerScan = () => http.post<ScanJob>('/scan/trigger')

export const fetchScanStatus = () => http.get<ScanJob | null>('/scan/status')
