import type { ReaderFitMode } from '@/types/reader'

const FIT_KEY = 'reader-fit'
const DEFAULT: ReaderFitMode = 'width'
export const READER_FIT_MAX_WIDTH = 960

const MODES: ReaderFitMode[] = ['width', 'screen', 'limit', 'original']

export const getStoredReaderFit = (): ReaderFitMode => {
  const raw = localStorage.getItem(FIT_KEY)
  return MODES.includes(raw as ReaderFitMode) ? (raw as ReaderFitMode) : DEFAULT
}

export const saveReaderFit = (fit: ReaderFitMode) => localStorage.setItem(FIT_KEY, fit)
