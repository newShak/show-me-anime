<template>
  <el-dialog v-model="visible" :title="detail?.title ?? '相册详情'" width="820px" @closed="onClosed">
    <el-skeleton v-if="loading" :rows="8" animated />
    <template v-else-if="detail">
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
      <el-form label-width="88px">
        <el-form-item label="保存到">
          <DownloadPathPicker v-model="parentPath" :hint="targetHint" />
        </el-form-item>
      </el-form>
      <el-progress v-if="job" :percentage="job.progress" :status="jobStatus" />
      <p v-if="job?.message" class="job-msg">{{ job.message }}</p>
    </template>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button
        v-if="job?.status === 'failed'"
        type="warning"
        :loading="downloading"
        @click="onRetry"
      >
        重试
      </el-button>
      <el-button
        v-else
        type="primary"
        :loading="downloading"
        :disabled="!detail || job?.status === 'running'"
        @click="onDownload"
      >
        {{ job?.status === 'done' ? '已完成' : '下载到画廊' }}
      </el-button>
      <el-button v-if="job?.status === 'done'" type="success" @click="goBrowse">在画廊中查看</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createDownloadJob, fetchDownloadJob, fetchRemoteDetail, fetchRemotePreviews, retryDownloadJob } from '@/api/download'
import { apiErrorMessage } from '@/api/http'
import DownloadPathPicker from '@/components/DownloadPathPicker.vue'
import { albumFolderName, joinTargetPath, parentFromTarget } from '@/utils/downloadPath'
import type { DownloadJob, RemoteAlbum, RemoteDetail } from '@/types/download'

const props = defineProps<{ item: RemoteAlbum | null; previewBatchSize?: number }>()
const visible = defineModel<boolean>({ default: false })

const router = useRouter()
const loading = ref(false)
const loadingMore = ref(false)
const downloading = ref(false)
const detail = ref<RemoteDetail | null>(null)
const previewUrls = ref<string[]>([])
const previewHasMore = ref(false)
const previewTotal = ref(0)
const parentPath = ref('')
const job = ref<DownloadJob | null>(null)
const activeIndex = ref(0)

const jobStatus = computed(() => {
  if (job.value?.status === 'failed') return 'exception'
  if (job.value?.status === 'done') return 'success'
  return undefined
})

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
  parts.push(`${detail.value.page_count} P`)
  if (previewTotal.value) parts.push(`预览 ${previewUrls.value.length}/${previewTotal.value}`)
  if (detail.value.tags.length) parts.push(detail.value.tags.join(' · '))
  return parts.join(' · ')
})

const activePreview = computed(() => previewUrls.value[activeIndex.value] ?? '')

const targetPath = computed(() => {
  if (!detail.value) return ''
  const folder = albumFolderName(detail.value.title, detail.value.id)
  return joinTargetPath(parentPath.value, folder)
})

const targetHint = computed(() => (targetPath.value ? `将保存到：${targetPath.value}` : ''))

const load = async (item: RemoteAlbum) => {
  loading.value = true
  job.value = null
  activeIndex.value = 0
  try {
    const { data } = await fetchRemoteDetail(item.source, item.id)
    detail.value = data
    previewUrls.value = data.preview_urls
    previewHasMore.value = data.preview_has_more
    previewTotal.value = data.preview_total || data.preview_urls.length
    parentPath.value = data.default_parent_rel_path || parentFromTarget(data.default_target_rel_path)
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

const pollJob = async (jobId: string) => {
  for (let i = 0; i < 60; i++) {
    const { data } = await fetchDownloadJob(jobId)
    job.value = data
    if (data.status === 'done' || data.status === 'failed') {
      if (data.status === 'done') {
        ElMessage.success(data.message ?? '下载完成')
        if (data.skipped_files > 0) {
          ElMessage.warning('部分文件已存在被跳过，可在下载记录中强制覆盖')
        }
      } else {
        ElMessage.error(data.message ?? '下载失败')
      }
      return
    }
    await new Promise((r) => setTimeout(r, 300))
  }
}

const onRetry = async () => {
  if (!job.value) return
  downloading.value = true
  try {
    const { data } = await retryDownloadJob(job.value.id)
    job.value = data
    await pollJob(data.id)
  } catch {
    ElMessage.error('重试失败')
  } finally {
    downloading.value = false
  }
}

const onDownload = async () => {
  if (!props.item || !detail.value || !targetPath.value) return
  downloading.value = true
  try {
    const { data } = await createDownloadJob({
      source: props.item.source,
      album_id: props.item.id,
      title: detail.value.title.replace(/<[^>]+>/g, ''),
      target_rel_path: targetPath.value,
    })
    job.value = data
    if (data.target_existed) ElMessage.warning('目标路径已存在，将跳过已有文件')
    await pollJob(data.id)
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
  detail.value = null
  previewUrls.value = []
  previewHasMore.value = false
  previewTotal.value = 0
  parentPath.value = ''
  job.value = null
  activeIndex.value = 0
}

watch(
  () => [visible.value, props.item] as const,
  ([open, item]) => {
    if (open && item) load(item)
  },
)
</script>

<style scoped>
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

.job-msg {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--app-text-muted);
}
</style>
