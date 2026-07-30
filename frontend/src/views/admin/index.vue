<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="sidebar-brand">管理</div>
      <el-menu :default-active="route.path" router class="sidebar-menu">
        <el-menu-item index="/admin/settings">
          <el-icon><Setting /></el-icon>
          <span>配置</span>
        </el-menu-item>
        <el-menu-item index="/admin/tags">
          <el-icon><CollectionTag /></el-icon>
          <span>标签</span>
        </el-menu-item>
        <el-menu-item index="/admin/tasks">
          <el-icon><List /></el-icon>
          <span>任务执行记录</span>
        </el-menu-item>
      </el-menu>
    </aside>

    <main class="main">
      <header class="main-head">
        <h2>{{ pageTitle }}</h2>
        <el-button :loading="refreshing" @click="onRefresh">
          <el-icon v-if="!refreshing"><Refresh /></el-icon>
          刷新
        </el-button>
      </header>
      <div class="main-body">
        <router-view :key="refreshKey" />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { CollectionTag, List, Refresh, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const route = useRoute()
const refreshKey = ref(0)
const refreshing = ref(false)

const pageTitle = computed(() => (route.meta.title as string) ?? '管理')

const onRefresh = async () => {
  refreshing.value = true
  try {
    refreshKey.value++
    ElMessage.success('已刷新')
  } finally {
    refreshing.value = false
  }
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: calc(100vh - 52px);
  background: var(--el-bg-color-page);
}

.sidebar {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
}

.sidebar-brand {
  padding: 20px 20px 12px;
  font-size: 15px;
  font-weight: 600;
}

.sidebar-menu {
  border-right: none;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.main-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px 0;
}

.main-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.main-body {
  flex: 1;
  padding: 16px 24px 32px;
}

@media (max-width: 768px) {
  .admin-layout {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  .sidebar-brand {
    padding: 12px 16px 0;
  }

  .sidebar-menu {
    display: flex;
    overflow-x: auto;
  }

  .sidebar-menu :deep(.el-menu-item) {
    flex-shrink: 0;
  }

  .main-head,
  .main-body {
    padding-left: 16px;
    padding-right: 16px;
  }
}
</style>
