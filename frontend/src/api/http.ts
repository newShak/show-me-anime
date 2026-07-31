import axios from 'axios'

export const http = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export const apiErrorMessage = (err: unknown, fallback: string) => {
  if (!axios.isAxiosError(err)) return fallback
  const detail = err.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}
