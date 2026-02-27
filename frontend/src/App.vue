<template>
  <div id="app">
    <el-container>
      <el-header>
        <nav-bar />
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
    
    <!-- 冲突处理组件 -->
    <ConflictNotification />
    <ConflictDialog />
    
    <!-- 离线状态指示器 -->
    <offline-indicator />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import NavBar from './components/NavBar.vue'
import OfflineIndicator from './components/OfflineIndicator.vue'
import ConflictNotification from './components/ConflictNotification.vue'
import ConflictDialog from './components/ConflictDialog.vue'
import { useLocalStorage } from './utils/localStorageService'
import { useSync } from './utils/syncService'
import { useNetwork } from './utils/networkMonitor'
import { offlineSyncService } from './services/offlineSync'

// 初始化离线支持服务
onMounted(() => {
  const { init } = useLocalStorage()
  const { startSync } = useSync()
  const { addNetworkListener } = useNetwork()
  
  // 初始化本地存储
  init().catch(error => {
    console.error('本地存储初始化失败:', error)
  })
  
  // 启动同步服务
  startSync()
  
  // 初始化离线同步服务（必须在Pinia激活后）
  offlineSyncService.initStore()
  
  // 监听网络状态变化
  addNetworkListener((event) => {
    console.log('网络状态变化:', event)
    // 网络恢复时触发同步
    if (event.type === 'online') {
      offlineSyncService.triggerSync()
    }
  })
})
</script>

<style>
#app {
  height: 100vh;
}

.el-header {
  padding: 0;
  box-shadow: 0 2px 4px rgba(0,0,0,.1);
}
</style>