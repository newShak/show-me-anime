<template>
  <el-dialog v-model="visible" :title="detail?.title ?? '相册详情'" :width="dialogWidth" @closed="onClosed">
    <el-skeleton v-if="loading" :rows="8" animated />
    <template v-else-if="detail">
      <template v-if="isSeries">
        <div class="series-head">
          <img :src="detail.cover_url" class="series-cover" alt="" />
          <div class="series-info">
            <p class="series-title">{{ detail.title }}</p>
            <p class="meta">{{ metaLine }}</p>
          </div>
        </div>
        <div class="chapter-bar">
          <el-checkbox
            :model-value="allSelected"
            :indeterminate="someSelected"
            @change="onToggleAll"
          >
            全选
          </el-checkbox>
          <span class="chapter-hint">已选 {{ selectedIds.length }} / {{ chapters.length }} 话</span>
        </div>
        <el-checkbox-group v-model="selectedIds" class="chapter-list">
          <div v-for="ch in chapters" :key="ch.id" class="chapter-row">
            <el-checkbox :value="ch.id" class="ch-check" />
            <span class="ch-idx">第{{ ch.index }}話</span>
            <span class="ch-name" :title="ch.name">{{ ch.name }}</span>
            <span class="ch-pages">{{ ch.page_count }}P</span>
          </div>
        </el-checkbox-group>
      </template>
      <template v-else>
        <div v-if="previewUrls.length" class="preview-main">
          <img :src="activePreview" class="preview-large" alt="" />
        </div>
        <div v-if="previewUrls.length > 1" class="preview-row">
          <button
            v-for="(url, idx) in previewUrls"
            :key="idx"
            type="button"
            class="thumb-btn"
            :class="{ active: idx === activeIndex }"
            @click="activeIndex = idx"
          >
            <img :src="url" class="preview" alt="" />
          </button>
        </div>
        <div v-if="previewHasMore" class="load-more">
          <el-button :loading="loadingMore" @click="loadMore">加载更多预览</el-button>
          <span class="load-hint">已显示 {{ previewUrls.length }} / {{ previewTotal }}</span>
        </div>
        <p class="meta">{{ metaLine }}</p>
      </template>

      <el-form label-width="88px">
        <el-form-item label="保存到">
          <DownloadPathPicker v-model="parentPath" :hint="targetHint" />
        </el-form-item>
        <el-form-item label="标签">
          <DownloadTagSection ref="tagSectionRef" :remote-tags="detail.tags" />
        </el-form-item>
      </el-form>

      <DownloadJobProgress
        v-if="jobs.length"
        :jobs="jobs"
        :retrying-id="retryingId"
        :status="jobStatus"
        @retry="retryJob"
      />
    </template>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button v-if="hasFailed && !running" :loading="retryingAll" @click="retryFailed">
        重试失败项
      </el-button>
      <el-button
        v-if="!jobs.length"
        type="primary"
        :loading="downloading"
        :disabled="primaryDisabled"
        @click="onDownload"
      >
        {{ primaryLabel }}
      </el-button>
      <el-button v-if="allDone" type="success" @click="goBrowse">在画廊中查看</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  createDownloadJob,
  createDownloadJobsBatch,
  fetchRemoteDetail,
  fetchRemotePreviews,
} from '@/api/download'
import { apiErrorMessage } from '@/api/http'
import DownloadJobProgress from '@/components/DownloadJobProgress.vue'
import DownloadPathPicker from '@/components/DownloadPathPicker.vue'
import DownloadTagSection from '@/components/DownloadTagSection.vue'
import { useDialogWidth } from '@/composables/useDialogWidth'
import { useJobPolling } from '@/composables/useJobPolling'
import { getDownloadParentPath, saveDownloadParentPath } from '@/composables/useDownloadParentPath'
import { albumFolderName, joinTargetPath, parentFromTarget } from '@/utils/downloadPath'
import type { RemoteAlbum, RemoteChapter, RemoteDetail } from '@/types/download'

const props = defineProps<{ item: RemoteAlbum | null; previewBatchSize?: number }>()
const visible = defineModel<boolean>({ default: false })
const dialogWidth = useDialogWidth('820px')

const router = useRouter()
const loading = ref(false)
const loadingMore = ref(false)
const downloading = ref(false)
const detail = ref<RemoteDetail | null>(null)
const previewUrls = ref<string[]>([])
const previewHasMore = ref(false)
const previewTotal = ref(0)
const parentPath = ref('')
const activeIndex = ref(0)
const selectedIds = ref<string[]>([])
const tagSectionRef = ref<InstanceType<typeof DownloadTagSection> | null>(null)

const {
  jobs,
  running,
  hasFailed,
  retryingId,
  retryingAll,
  jobStatus,
  pollJobs,
  retryJob,
  retryFailed,
  reset,
} = useJobPolling()

const isSeries = computed(() => detail.value?.is_series === true)
const chapters = computed<RemoteChapter[]>(() => detail.value?.chapters ?? [])

const allSelected = computed(
  () => chapters.value.length > 0 && selectedIds.value.length === chapters.value.length,
)
const someSelected = computed(
  () => selectedIds.value.length > 0 && selectedIds.value.length < chapters.value.length,
)
const allDone = computed(() => jobs.value.length > 0 && jobs.value.every((j) => j.status === 'done'))

const onToggleAll = (checked: boolean | string | number) => {
  selectedIds.value = checked ? chapters.value.map((c) => c.id) : []
}

const metaLine = computed(() => {
  if (!detail.value) return ''
  const parts: string[] = []
  if (detail.value.category && detail.value.language) {
    parts.push(`${detail.value.category} / ${detail.value.language}`)
  } else if (detail.value.language) {
    parts.push(detail.value.language)
  } else if (detail.value.category) {
    parts.push(detail.value.category)
  }
  if (isSeries.value) {
    parts.push(`合集 · 共 ${detail.value.chapter_count || chapters.value.length} 話`)
    parts.push(`合计 ${detail.value.page_count} P`)
  } else {
    parts.push(`${detail.value.page_count} P`)
    if (previewTotal.value) parts.push(`预览 ${previewUrls.value.length}/${previewTotal.value}`)
  }
  return parts.join(' · ')
})

const activePreview = computed(() => previewUrls.value[activeIndex.value] ?? '')

const seriesFolder = computed(() =>
  detail.value ? albumFolderName(detail.value.title, detail.value.id) : '',
)

const targetPath = computed(() => {
  if (!detail.value) return ''
  return joinTargetPath(parentPath.value, seriesFolder.value)
})

const chapterTitle = (ch: RemoteChapter) => `第${ch.index}話 ${ch.name}`

const targetHint = computed(() => {
  if (!targetPath.value) return ''
  if (!isSeries.value) return `将保存到：${targetPath.value}`
  const sample = chapters.value[0]
  const example = sample ? albumFolderName(chapterTitle(sample), sample.id) : '第1話 …'
  return `每一话一个子文件夹：${targetPath.value}/${example}`
})

const primaryLabel = computed(() =>
  isSeries.value ? `下载选中的 ${selectedIds.value.length} 话` : '下载到画廊',
)

const primaryDisabled = computed(() => {
  if (!detail.value || running.value) return true
  return isSeries.value && selectedIds.value.length === 0
})

const load = async (item: RemoteAlbum) => {
  reset()
  loading.value = true
  downloading.value = false
  activeIndex.value = 0
  selectedIds.value = []
  try {
    const { data } = await fetchRemoteDetail(item.source, item.id)
    detail.value = data
    previewUrls.value = data.preview_urls
    previewHasMore.value = data.preview_has_more
    previewTotal.value = data.preview_total || data.preview_urls.length
    selectedIds.value = data.chapters.map((c) => c.id)
    parentPath.value =
      getDownloadParentPath() ||
      data.default_parent_rel_path ||
      parentFromTarget(data.default_target_rel_path)
  } catch {
    ElMessage.error('加载详情失败')
    visible.value = false
  } finally {
    loading.value = false
  }
}

const loadMore = async () => {
  if (!props.item || !previewHasMore.value || loadingMore.value) return
  loadingMore.value = true
  try {
    const { data } = await fetchRemotePreviews(
      props.item.source,
      props.item.id,
      previewUrls.value.length,
      props.previewBatchSize,
    )
    previewUrls.value = [...previewUrls.value, ...data.preview_urls]
    previewHasMore.value = data.has_more
    previewTotal.value = data.total
  } catch {
    ElMessage.error('加载更多预览失败')
  } finally {
    loadingMore.value = false
  }
}

const onDownload = async () => {
  if (!props.item || !detail.value || !targetPath.value) return
  saveDownloadParentPath(parentPath.value)
  downloading.value = true
  try {
    const tags = tagSectionRef.value?.getPayload() ?? { tag_ids: [], import_remote_tags: [] }
    if (isSeries.value) {
      const picked = chapters.value.filter((c) => selectedIds.value.includes(c.id))
      if (!picked.length) return
      const { data } = await createDownloadJobsBatch({
        parent_rel_path: targetPath.value,
        tag_ids: tags.tag_ids,
        items: picked.map((c) => ({
          source: props.item!.source,
          album_id: c.id,
          title: chapterTitle(c),
          import_remote_tags: tags.import_remote_tags,
        })),
      })
      reset(data.jobs)
      if (data.jobs.some((j) => j.target_existed)) {
        ElMessage.warning('部分目标路径已存在，将跳过下载')
      }
      await pollJobs()
      return
    }
    const { data } = await createDownloadJob({
      source: props.item.source,
      album_id: props.item.id,
      title: detail.value.title.replace(/<[^>]+>/g, ''),
      target_rel_path: targetPath.value,
      tag_ids: tags.tag_ids,
      import_remote_tags: tags.import_remote_tags,
    })
    reset([data])
    if (data.target_existed) ElMessage.warning('目标路径已存在，将跳过下载')
    await pollJobs()
  } catch (e) {
    ElMessage.error(apiErrorMessage(e, '创建下载任务失败'))
  } finally {
    downloading.value = false
  }
}

const goBrowse = () => {
  visible.value = false
  router.push('/browse')
}

const onClosed = () => {
  reset()
  detail.value = null
  previewUrls.value = []
  previewHasMore.value = false
  previewTotal.value = 0
  parentPath.value = ''
  selectedIds.value = []
  downloading.value = false
  activeIndex.value = 0
  tagSectionRef.value?.reset()
}

watch(
  () => [visible.value, props.item] as const,
  ([open, item]) => {
    if (open && item) load(item)
  },
)
</script>

<style scoped>
.series-head {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.series-cover {
  width: 108px;
  height: 152px;
  object-fit: cover;
  border-radius: 8px;
  background: var(--app-cover-bg);
  flex-shrink: 0;
}

.series-info {
  min-width: 0;
}

.series-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
}

.chapter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 0 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.chapter-hint {
  font-size: 12px;
  color: var(--app-text-muted);
}

.chapter-list {
  display: block;
  max-height: 280px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.chapter-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 0;
  font-size: 13px;
}

.ch-check {
  flex-shrink: 0;
  margin-right: 0;
}

.ch-idx {
  flex-shrink: 0;
  color: var(--el-color-primary);
  font-weight: 600;
}

.ch-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ch-pages {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--app-text-muted);
}

.preview-main {
  margin-bottom: 12px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--app-cover-bg);
}

.preview-large {
  display: block;
  width: 100%;
  max-height: 420px;
  object-fit: contain;
  margin: 0 auto;
}

.preview-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  max-height: 220px;
  overflow-y: auto;
  padding-bottom: 4px;
}

.thumb-btn {
  padding: 0;
  border: 2px solid transparent;
  border-radius: 6px;
  background: none;
  cursor: pointer;
  flex-shrink: 0;
}

.thumb-btn.active {
  border-color: var(--el-color-primary);
}

.preview {
  display: block;
  width: 72px;
  height: 96px;
  object-fit: cover;
  border-radius: 4px;
  background: var(--app-cover-bg);
}

.load-more {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.load-hint {
  font-size: 12px;
  color: var(--app-text-muted);
}

.meta {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--app-text-muted);
}
</style>
