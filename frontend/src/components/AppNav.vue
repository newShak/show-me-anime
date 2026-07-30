<template>
  <nav class="app-nav">
    <router-link to="/browse" class="brand">
      <span class="logo" />
      show-me-anime
    </router-link>
    <div class="right">
      <div class="links">
        <router-link to="/" exact-active-class="active">首页</router-link>
        <a :class="{ active: isGallery }" href="#" @click.prevent="$router.push('/browse')">画廊</a>
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
  </nav>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { applyTheme, getTheme, type ThemeMode } from '@/composables/useTheme'

const route = useRoute()
const isGallery = computed(() => route.path.startsWith('/browse') || route.path === '/search')
const isAdmin = computed(() => route.path.startsWith('/admin'))

const theme = ref<ThemeMode>(getTheme())

const onThemeChange = (dark: string | number | boolean) => {
  const mode: ThemeMode = dark ? 'dark' : 'light'
  theme.value = mode
  applyTheme(mode)
}
</script>

<style scoped>
.app-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  height: 52px;
  background: var(--app-surface);
  border-bottom: 1px solid var(--app-border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 15px;
  color: var(--app-text);
  text-decoration: none;
}

.logo {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--el-color-primary);
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
</style>
