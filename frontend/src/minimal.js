import { createApp } from 'vue'

const app = createApp({
  data() {
    return {
      message: 'Vue应用正常运行！',
      apiStatus: '未知'
    }
  },
  async mounted() {
    try {
      const response = await fetch('/api/')
      if (response.ok) {
        this.apiStatus = '连接正常'
      } else {
        this.apiStatus = `HTTP ${response.status}`
      }
    } catch (error) {
      this.apiStatus = `错误: ${error.message}`
    }
  },
  template: `
    <div style="padding: 20px; font-family: Arial;">
      <h1>{{ message }}</h1>
      <p>API状态: {{ apiStatus }}</p>
      <button @click="location.reload()">刷新页面</button>
    </div>
  `
})

app.mount('#app')