import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('@/views/home/index.vue') },
    { path: '/browse', component: () => import('@/views/browse/index.vue') },
    { path: '/browse/:nodeId', component: () => import('@/views/browse/index.vue') },
    { path: '/reader/:nodeId', component: () => import('@/views/reader/index.vue') },
  ],
})

export default router
