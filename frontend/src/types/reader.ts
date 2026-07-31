export type ReaderMode = 'page' | 'scroll'

export type ReaderFitMode = 'width' | 'screen' | 'limit' | 'original'

export type ReaderFitOption = { label: string; value: ReaderFitMode }

export const READER_FIT_OPTIONS: ReaderFitOption[] = [
  { label: '适应宽度', value: 'width' },
  { label: '适应屏幕', value: 'screen' },
  { label: '限定宽度', value: 'limit' },
  { label: '原始比例', value: 'original' },
]
