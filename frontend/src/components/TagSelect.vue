<template>
  <el-select
    v-model="model"
    :multiple="multiple"
    filterable
    reserve-keyword
    default-first-option
    :clearable="clearable"
    :collapse-tags="collapseTags"
    :collapse-tags-tooltip="collapseTags"
    :placeholder="placeholder"
    :style="{ width }"
    @change="(val: number | number[]) => emit('change', val)"
  >
    <el-option v-for="tag in tags" :key="tag.id" :label="tag.name" :value="tag.id" />
  </el-select>
</template>

<script setup lang="ts">
import type { TagItem } from '@/types/tag'

withDefaults(
  defineProps<{
    tags: TagItem[]
    multiple?: boolean
    placeholder?: string
    clearable?: boolean
    collapseTags?: boolean
    width?: string
  }>(),
  {
    multiple: true,
    placeholder: '搜索标签',
    clearable: false,
    collapseTags: false,
    width: '100%',
  },
)

const model = defineModel<number | number[]>()

const emit = defineEmits<{ change: [value: number | number[]] }>()
</script>
