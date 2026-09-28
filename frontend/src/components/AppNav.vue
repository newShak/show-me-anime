<template>
  <nav class="app-nav">
    <div class="brand-wrap">
      <router-link to="/browse" class="brand" :title="versionTitle">
        <span class="logo" />
        <span class="brand-name">show-me-anime</span>
        <span class="version">v{{ appVersion }}</span>
      </router-link>
      <el-tag size="small" :type="healthOk ? 'success' : 'danger'" class="health" :class="{ compact: isMobile }">
        {{ healthOk ? '已连接' : '未连接' }}
      </el-tag>
    </div>
    <div v-if="!isMobile" class="right">
      <div class="links">
        <router-link to="/" exact-active-class="active">首页</router-link>
        <a :class="{ active: isGallery }" href="#" @click.prevent="$router.push('/browse')">画廊</a>
        <router-link to="/download" active-class="active">下载</router-link>
        <a :class="{ active: isAdmin }" href="#" @click.prevent="$router.push('/admin/settings')">管理</a>
      </div>
      <el-switch
        :model-value="theme === 'dark'"
        inline-prompt
        active-text="暗"
        inactive-text="亮"
        @change="onThemeChange"
      />
    </div>
    <el-button v-else class="menu-btn" text circle aria-label="打开菜单" @click="menuOpen = true">
      <el-icon :size="20"><Menu /></el-icon>
    </el-button>

    <el-drawer
      v-model="menuOpen"
      direction="rtl"
      size="min(260px, 78vw)"
      title="菜单"
      class="nav-drawer"
      append-to-body
    >
      <div class="mobile-menu">
        <router-link to="/" class="mobile-link" exact-active-class="active" @click="menuOpen = false">首页</router-link>
        <router-link to="/browse" class="mobile-link" active-class="active" @click="menuOpen = false">画廊</router-link>
        <router-link to="/download" class="mobile-link" active-class="active" @click="menuOpen = false">下载</router-link>
        <router-link to="/admin/settings" class="mobile-link" active-class="active" @click="menuOpen = false">管理</router-link>
        <div class="mobile-theme">
          <span>主题</span>
          <el-switch
            :model-value="theme === 'dark'"
            inline-prompt
            active-text="暗"
            inactive-text="亮"
            @change="onThemeChange"
          />
        </div>
        <p class="mobile-version" :class="{ warn: versionMismatch }">{{ versionTitle }}</p>
      </div>
    </el-drawer>
  </nav>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Menu } from '@element-plus/icons-vue'
import { fetchHealth } from '@/api/settings'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { applyTheme, getTheme, type ThemeMode } from '@/composables/useTheme'

const route = useRoute()
const { isMobile } = useBreakpoint()

const isGallery = computed(() => route.path.startsWith('/browse') || route.path === '/search')
const isAdmin = computed(() => route.path.startsWith('/admin'))

const theme = ref<ThemeMode>(getTheme())
const healthOk = ref(false)
const serverVersion = ref<string | null>(null)
const menuOpen = ref(false)

const appVersion = __APP_VERSION__

const versionMismatch = computed(
  () => !!serverVersion.value && serverVersion.value !== appVersion,
)

const versionTitle = computed(() => {
  if (!serverVersion.value) return `前端 v${appVersion}`
  if (!versionMismatch.value) return `v${appVersion}`
  return `前端 v${appVersion} · 后端 v${serverVersion.value}（不一致，请重新构建前端）`
})

const onThemeChange = (dark: string | number | boolean) => {
  const mode: ThemeMode = dark ? 'dark' : 'light'
  theme.value = mode
  applyTheme(mode)
}

onMounted(async () => {
  try {
    const { data } = await fetchHealth()
    healthOk.value = true
    serverVersion.value = data.version ?? null
  } catch {
    healthOk.value = false
    serverVersion.value = null
  }
})
</script>

<style scoped>
.app-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--app-page-padding);
  height: var(--app-nav-height);
  padding-top: env(safe-area-inset-top, 0px);
  background: var(--app-surface);
  border-bottom: 1px solid var(--app-border);
}

.brand-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-weight: 600;
  font-size: 15px;
  color: var(--app-text);
  text-decoration: none;
}

.brand-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logo {
  width: 10px;
  height: 10px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--el-color-primary);
}

.version {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 500;
  color: var(--app-text-muted);
}

.health {
  flex-shrink: 0;
}

.right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.links {
  display: flex;
  gap: 24px;
}

.links a {
  color: var(--app-text-muted);
  text-decoration: none;
  font-size: 13px;
  letter-spacing: 0.02em;
  transition: color 0.15s;
}

.links a:hover {
  color: var(--app-text);
}

.links a.active,
.links a.router-link-active {
  color: var(--el-color-primary);
  font-weight: 600;
}

.menu-btn {
  flex-shrink: 0;
}

.mobile-menu {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mobile-link {
  display: block;
  padding: 12px 8px;
  font-size: 15px;
  color: var(--app-text);
  text-decoration: none;
  border-radius: 8px;
}

.mobile-link.active,
.mobile-link.router-link-active {
  color: var(--el-color-primary);
  font-weight: 600;
  background: color-mix(in srgb, var(--el-color-primary) 12%, transparent);
}

.mobile-theme {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding: 12px 8px;
  font-size: 14px;
  color: var(--app-text-secondary);
}

.mobile-version {
  margin: 16px 8px 0;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  font-size: 12px;
  color: var(--app-text-muted);
  line-height: 1.5;
  word-break: break-word;
}

.mobile-version.warn {
  color: var(--el-color-warning);
}

@media (max-width: 767px) {
  .version {
    display: none;
  }

  .brand-name {
    font-size: 14px;
  }

  .health.compact :deep(.el-tag__content) {
    font-size: 11px;
  }

  .health.compact {
    padding: 0 6px;
    height: 22px;
  }
}
</style>
