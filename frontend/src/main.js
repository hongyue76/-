import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

// 导入所有store
import { useAuthStore } from './stores/auth'
import { useTodosStore } from './stores/todos'
import { useSharedListsStore } from './stores/sharedLists'
import { useCommentsStore } from './stores/comments'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus)

app.mount('#app')