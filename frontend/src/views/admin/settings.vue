<template>
  <div class="settings-page">
    <el-card shadow="never" class="panel">
      <template #header><span class="panel-title">路径与监听</span></template>
      <el-form v-if="form" label-width="96px" class="settings-form">
        <section class="form-block">
          <h3 class="block-title">存储路径</h3>
          <el-form-item label="画廊根目录">
            <el-input v-model="form.gallery_root" />
          </el-form-item>
          <el-form-item label="缩略图目录">
            <el-input v-model="form.thumb_dir" />
          </el-form-item>
        </section>

        <section class="form-block">
          <h3 class="block-title">缩略图</h3>
          <el-form-item label="最大尺寸">
            <el-input-number v-model="form.thumb_max_size" :min="64" :max="2000" />
          </el-form-item>
          <el-form-item label="缓存">
            <el-button :loading="rebuildingThumbs" @click="onRebuildThumbs">重建缩略图</el-button>
          </el-form-item>
        </section>

        <section class="form-block">
          <h3 class="block-title">目录监听</h3>
          <el-form-item label="启用监听">
            <el-switch v-model="form.watch_enabled" />
          </el-form-item>
          <el-form-item label="防抖秒数">
            <el-input-number v-model="form.watch_debounce_seconds" :min="1" :max="60" />
          </el-form-item>
        </section>

        <div class="form-footer">
          <el-button type="primary" :loading="savingSettings" @click="onSaveSettings">保存配置</el-button>
        </div>
      </el-form>
      <el-skeleton v-else :rows="8" animated />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchSettings, rebuildThumbs, saveSettings } from '@/api/settings'
import type { Settings } from '@/types/settings'

const form = ref<Settings | null>(null)
const savingSettings = ref(false)
const rebuildingThumbs = ref(false)

const load = async () => {
  const { data } = await fetchSettings()
  form.value = { ...data }
}

const onSaveSettings = async () => {
  if (!form.value) return
  savingSettings.value = true
  try {
    const { data } = await saveSettings({
      gallery_root: form.value.gallery_root,
      thumb_dir: form.value.thumb_dir,
      thumb_max_size: form.value.thumb_max_size,
      watch_enabled: form.value.watch_enabled,
      watch_debounce_seconds: form.value.watch_debounce_seconds,
    })
    form.value = { ...data }
    ElMessage.success(data.message ?? '配置已保存')
    if (data.needs_rescan) ElMessage.warning('画廊根目录已变更，请到任务执行记录页重新扫描')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingSettings.value = false
  }
}

const onRebuildThumbs = async () => {
  try {
    await ElMessageBox.confirm(
      '将清空缩略图缓存目录，下次浏览相册时会按当前尺寸重新生成。原图不受影响。',
      '重建缩略图',
      { type: 'warning', confirmButtonText: '重建', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  rebuildingThumbs.value = true
  try {
    const { data } = await rebuildThumbs()
    ElMessage.success(data.message)
  } catch {
    ElMessage.error('重建失败')
  } finally {
    rebuildingThumbs.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.settings-page {
  max-width: 640px;
}

.panel {
  border: 1px solid var(--el-border-color-lighter);
}

.panel :deep(.el-card__header) {
  padding: 12px 16px;
}

.panel :deep(.el-card__body) {
  padding: 16px;
}

.panel-title {
  font-weight: 600;
  font-size: 14px;
}

.form-block + .form-block {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.block-title {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}

.settings-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.form-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
