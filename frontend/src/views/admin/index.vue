<template>
  <div class="admin">
    <header class="head">
      <h1>管理</h1>
      <div class="links">
        <el-button link type="primary" @click="$router.push('/')">首页</el-button>
        <el-button link type="primary" @click="$router.push('/browse')">画廊</el-button>
      </div>
    </header>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" header="路径与监听">
          <el-form v-if="form" label-width="120px">
            <el-form-item label="画廊根目录">
              <el-input v-model="form.gallery_root" />
            </el-form-item>
            <el-form-item label="缩略图目录">
              <el-input v-model="form.thumb_dir" />
            </el-form-item>
            <el-form-item label="缩略图尺寸">
              <el-input-number v-model="form.thumb_max_size" :min="64" :max="2000" />
            </el-form-item>
            <el-form-item label="目录监听">
              <el-switch v-model="form.watch_enabled" />
            </el-form-item>
            <el-form-item label="防抖秒数">
              <el-input-number v-model="form.watch_debounce_seconds" :min="1" :max="60" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingSettings" @click="onSaveSettings">保存配置</el-button>
            </el-form-item>
          </el-form>
          <el-skeleton v-else :rows="6" animated />
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="never" header="扫描">
          <el-button type="primary" :loading="scanning" @click="onScan">触发扫描</el-button>
          <el-descriptions v-if="scanJob" :column="1" border class="scan-info">
            <el-descriptions-item label="状态">{{ scanJob.status }}</el-descriptions-item>
            <el-descriptions-item label="新增">{{ scanJob.added }}</el-descriptions-item>
            <el-descriptions-item label="更新">{{ scanJob.updated }}</el-descriptions-item>
            <el-descriptions-item label="移除">{{ scanJob.removed }}</el-descriptions-item>
            <el-descriptions-item v-if="scanJob.message" label="消息">
              {{ scanJob.message }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never" header="标签" class="tag-card">
          <div class="tag-add">
            <el-input v-model="newTag" placeholder="新标签名" @keyup.enter="onAddTag" />
            <el-button type="primary" :loading="addingTag" @click="onAddTag">添加</el-button>
          </div>
          <el-table :data="tags" size="small" empty-text="暂无标签">
            <el-table-column prop="name" label="名称" />
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button link type="danger" @click="onDeleteTag(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchScanStatus, triggerScan } from '@/api/scan'
import { fetchSettings, saveSettings } from '@/api/settings'
import { createTag, deleteTag, fetchTags } from '@/api/tags'
import type { ScanJob } from '@/types/node'
import type { Settings } from '@/types/settings'
import type { TagItem } from '@/types/tag'

const form = ref<Settings | null>(null)
const savingSettings = ref(false)
const scanning = ref(false)
const scanJob = ref<ScanJob | null>(null)
const tags = ref<TagItem[]>([])
const newTag = ref('')
const addingTag = ref(false)

const load = async () => {
  const [settingsRes, tagsRes, scanRes] = await Promise.all([
    fetchSettings(),
    fetchTags(),
    fetchScanStatus(),
  ])
  form.value = { ...settingsRes.data }
  tags.value = tagsRes.data
  scanJob.value = scanRes.data
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
    if (data.needs_rescan) {
      ElMessage.warning('画廊根目录已变更，请重新扫描')
    }
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingSettings.value = false
  }
}

const onScan = async () => {
  scanning.value = true
  try {
    const { data } = await triggerScan()
    scanJob.value = data
    ElMessage.success(`扫描完成：新增 ${data.added}，更新 ${data.updated}`)
  } catch {
    ElMessage.error('扫描失败')
  } finally {
    scanning.value = false
  }
}

const onAddTag = async () => {
  const name = newTag.value.trim()
  if (!name) return
  addingTag.value = true
  try {
    await createTag(name)
    newTag.value = ''
    tags.value = (await fetchTags()).data
    ElMessage.success('标签已添加')
  } catch {
    ElMessage.error('添加失败')
  } finally {
    addingTag.value = false
  }
}

const onDeleteTag = async (id: number) => {
  try {
    await ElMessageBox.confirm('删除后节点上的该标签也会移除', '确认删除')
    await deleteTag(id)
    tags.value = (await fetchTags()).data
    ElMessage.success('已删除')
  } catch {
    /* cancel or error */
  }
}

onMounted(load)
</script>

<style scoped>
.admin {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.head h1 {
  margin: 0;
  font-size: 22px;
}

.links {
  display: flex;
  gap: 8px;
}

.scan-info {
  margin-top: 16px;
}

.tag-card {
  margin-top: 16px;
}

.tag-add {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
</style>
