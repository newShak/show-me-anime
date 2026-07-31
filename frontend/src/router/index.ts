import { createRouter, createWebHistory } from 'vue-router'
import { hasBrowseScroll } from '@/composables/useBrowseScroll'

const browseNodeId = (params: Record<string, string | string[] | undefined>) => {
  const raw = params.nodeId
  if (raw == null || Array.isArray(raw)) return null
  return Number(raw)
}

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, _from, savedPosition) {
    if (to.path.startsWith('/browse') && hasBrowseScroll(browseNodeId(to.params))) {
      return false
    }
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
  routes: [
    { path: '/', component: () => import('@/views/home/index.vue') },
    {
      path: '/recent-added',
      component: () => import('@/views/home/recent-added.vue'),
    },
    {
      path: '/recent-viewed',
      component: () => import('@/views/home/section.vue'),
      meta: { section: 'viewed' },
    },
    {
      path: '/favorites',
      component: () => import('@/views/home/section.vue'),
      meta: { section: 'favorites' },
    },
    { path: '/browse', component: () => import('@/views/browse/index.vue') },
    { path: '/browse/:nodeId', component: () => import('@/views/browse/index.vue') },
    { path: '/reader/:nodeId', component: () => import('@/views/reader/index.vue') },
    { path: '/search', component: () => import('@/views/search/index.vue') },
    { path: '/download', component: () => import('@/views/download/index.vue') },
    {
      path: '/admin',
      component: () => import('@/views/admin/index.vue'),
      redirect: '/admin/settings',
      children: [
        {
          path: 'settings',
          component: () => import('@/views/admin/settings.vue'),
          meta: { title: '配置' },
        },
        {
          path: 'download',
          component: () => import('@/views/admin/download.vue'),
          meta: { title: '下载配置' },
        },
        {
          path: 'tags',
          component: () => import('@/views/admin/tags.vue'),
          meta: { title: '标签' },
        },
        {
          path: 'tasks',
          component: () => import('@/views/admin/tasks.vue'),
          meta: { title: '任务执行记录' },
        },
        {
          path: 'logs',
          component: () => import('@/views/admin/logs.vue'),
          meta: { title: '应用日志' },
        },
      ],
    },
  ],
})

export default router
