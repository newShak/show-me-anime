<template>
  <div class="download-settings">
    <el-card shadow="never" class="panel">
      <template #header><span class="panel-title">外站下载</span></template>
      <el-form v-if="form" label-width="120px" class="settings-form">
        <el-form-item label="Mock 模式">
          <el-switch v-model="form.download_use_mock" />
          <span class="hint">开启后使用假数据，不访问 wnacg</span>
        </el-form-item>
        <el-form-item label="启用代理">
          <el-switch v-model="form.download_proxy_enabled" />
        </el-form-item>
        <el-form-item label="代理地址">
          <el-input v-model="form.download_proxy" placeholder="http://127.0.0.1:7890" />
        </el-form-item>
        <el-form-item label="API 域名">
          <el-input v-model="form.download_api_domain" placeholder="www.wn07.ru" />
        </el-form-item>
        <el-form-item label="默认子目录">
          <el-input v-model="form.download_default_subdir" placeholder="imports/wnacg" />
          <span class="hint">相对画廊根目录，下载时预填保存路径</span>
        </el-form-item>
        <el-form-item label="下载缓存目录">
          <el-input v-model="form.download_cache_dir" placeholder="/data/cache" />
          <span class="hint">下载与解压完成前的工作目录，完成后自动搬入画廊并清理</span>
        </el-form-item>
        <el-form-item label="预览批次大小">
          <el-input-number v-model="form.download_preview_batch_size" :min="1" :max="50" />
          <span class="hint">详情页每次加载的预览图数量</span>
        </el-form-item>
        <el-form-item label="并发下载数">
          <el-input-number v-model="form.download_concurrency" :min="1" :max="10" />
          <span class="hint">同时进行的下载任务上限</span>
        </el-form-item>
        <el-form-item label="下载限速">
          <el-input-number v-model="form.download_speed_limit_kbps" :min="0" :max="102400" :step="512" />
          <span class="hint">KB/s，0 表示不限速</span>
        </el-form-item>
        <el-form-item label="连接测试">
          <el-button :loading="testingProxy" @click="onTestProxy">测试 wnacg 连通</el-button>
        </el-form-item>
        <el-form-item label="缓存">
          <el-button :loading="clearingCache" @click="onClearCache">清空下载缓存</el-button>
          <span class="hint">删除未完成或中断任务留下的临时文件</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="onSave">保存配置</el-button>
        </el-form-item>
      </el-form>
      <el-skeleton v-else :rows="6" animated />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchSettings, saveSettings } from '@/api/settings'
import { clearDownloadCache, testDownloadProxy } from '@/api/download'
import type { Settings } from '@/types/settings'

const form = ref<Settings | null>(null)
const saving = ref(false)
const testingProxy = ref(false)
const clearingCache = ref(false)

const load = async () => {
  const { data } = await fetchSettings()
  form.value = { ...data }
}

const onSave = async () => {
  if (!form.value) return
  saving.value = true
  try {
    const { data } = await saveSettings({
      download_proxy_enabled: form.value.download_proxy_enabled,
      download_proxy: form.value.download_proxy || undefined,
      download_default_subdir: form.value.download_default_subdir,
      download_use_mock: form.value.download_use_mock,
      download_api_domain: form.value.download_api_domain,
      download_preview_batch_size: form.value.download_preview_batch_size,
      download_concurrency: form.value.download_concurrency,
      download_speed_limit_kbps: form.value.download_speed_limit_kbps,
      download_cache_dir: form.value.download_cache_dir,
    })
    form.value = { ...data }
    ElMessage.success(data.message ?? '配置已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const onTestProxy = async () => {
  testingProxy.value = true
  try {
    const { data } = await testDownloadProxy()
    if (data.ok) ElMessage.success(`连通正常：${data.message}`)
    else ElMessage.warning(`无法访问：${data.message}`)
  } catch {
    ElMessage.error('测试失败')
  } finally {
    testingProxy.value = false
  }
}

const onClearCache = async () => {
  try {
    await ElMessageBox.confirm('将删除下载缓存目录中所有未完成的临时文件，是否继续？', '清空下载缓存')
  } catch {
    return
  }
  clearingCache.value = true
  try {
    const { data } = await clearDownloadCache()
    ElMessage.success(data.message)
  } catch {
    ElMessage.error('清空失败')
  } finally {
    clearingCache.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.download-settings {
  max-width: 640px;
}

.panel :deep(.el-card__header) {
  padding: 12px 16px;
}

.panel-title {
  font-weight: 600;
  font-size: 14px;
}

.settings-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.hint {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
</style>
