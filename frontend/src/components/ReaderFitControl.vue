<template>
  <el-segmented v-model="model" :options="READER_FIT_OPTIONS" size="small" />
</template>

<script setup lang="ts">
import { READER_FIT_OPTIONS, type ReaderFitMode } from '@/types/reader'

const model = defineModel<ReaderFitMode>({ required: true })
</script>
