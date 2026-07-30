import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('@/views/home/index.vue') },
    { path: '/browse', component: () => import('@/views/browse/index.vue') },
    { path: '/browse/:nodeId', component: () => import('@/views/browse/index.vue') },
    { path: '/reader/:nodeId', component: () => import('@/views/reader/index.vue') },
    { path: '/search', component: () => import('@/views/search/index.vue') },
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
          path: 'tags',
          component: () => import('@/views/admin/tags.vue'),
          meta: { title: '标签' },
        },
        {
          path: 'tasks',
          component: () => import('@/views/admin/tasks.vue'),
          meta: { title: '任务执行记录' },
        },
      ],
    },
  ],
})

export default router
