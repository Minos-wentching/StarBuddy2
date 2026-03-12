import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'

// 导入全局样式
import './assets/styles/tailwind.css'
import '@/design-system/tokens.css' // 设计系统令牌
import './assets/styles/persona-colors.css'
import './assets/styles/transitions.css'

// 创建应用
const app = createApp(App)

// 使用插件
app.use(createPinia())
app.use(router)
app.use(vuetify)

// 挂载应用
app.mount('#app')
