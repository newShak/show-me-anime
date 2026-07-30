import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import App from './App.vue'
import router from './router'
import { initTheme } from './composables/useTheme'
import './style.css'

initTheme()

createApp(App).use(router).use(ElementPlus).mount('#app')
