<template>
  <div class="home">
    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>show-me-anime</span>
          <div class="actions">
            <el-button type="primary" link @click="$router.push('/browse')">进入画廊</el-button>
            <el-tag :type="healthOk ? 'success' : 'danger'">
              {{ healthOk ? '后端已连接' : '后端未连接' }}
            </el-tag>
          </div>
        </div>
      </template>

      <el-skeleton v-if="loading" :rows="4" animated />
      <el-descriptions v-else-if="settings" :column="1" border>
        <el-descriptions-item label="画廊根目录">
          {{ settings.gallery_root }}
        </el-descriptions-item>
        <el-descriptions-item label="缩略图目录">
          {{ settings.thumb_dir }}
        </el-descriptions-item>
        <el-descriptions-item label="数据库">
          {{ settings.database_url }}
        </el-descriptions-item>
        <el-descriptions-item label="监听目录">
          {{ settings.watch_enabled ? '开启' : '关闭' }}
        </el-descriptions-item>
      </el-descriptions>

      <el-alert
        v-else
        type="warning"
        :closable="false"
        title="无法读取配置，请确认后端已启动。"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchHealth, fetchSettings } from '@/api/settings'
import type { Settings } from '@/types/settings'

const loading = ref(true)
const healthOk = ref(false)
const settings = ref<Settings | null>(null)

onMounted(async () => {
  try {
    await fetchHealth()
    healthOk.value = true
    const { data } = await fetchSettings()
    settings.value = data
  } catch {
    healthOk.value = false
    settings.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.home {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 18px;
  font-weight: 600;
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
