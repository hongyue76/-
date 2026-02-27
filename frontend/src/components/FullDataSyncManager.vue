<template>
  <div class="full-data-sync-manager">
    <!-- 同步状态指示器 -->
    <div 
      v-if="isSyncing" 
      class="sync-indicator"
      :class="{ 'background-mode': syncProgress.isBackground }"
    >
      <div class="indicator-content">
        <el-progress 
          type="circle" 
          :percentage="Math.round(syncProgress.percentage)"
          :width="80"
          :stroke-width="6"
        />
        <div class="indicator-text">
          <div class="main-text">{{ getSyncStatusText() }}</div>
          <div class="sub-text">{{ getSyncSubText() }}</div>
        </div>
      </div>
      
      <!-- 后台同步模式下的轻量提示 -->
      <div v-if="syncProgress.isBackground" class="background-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>数据同步在后台进行，不影响您的操作</span>
      </div>
    </div>

    <!-- 手动同步按钮 -->
    <div v-if="!isSyncing" class="manual-sync">
      <el-button 
        type="primary" 
        @click="triggerFullSync"
        :loading="isTriggering"
        size="small"
      >
        <el-icon><Refresh /></el-icon>
        同步云端数据
      </el-button>
      <el-button 
        @click="triggerIncrementalSync"
        :loading="isIncrementalSyncing"
        size="small"
      >
        <el-icon><Sort /></el-icon>
        增量同步
      </el-button>
    </div>

    <!-- 同步详情面板 -->
    <el-drawer
      v-model="showDetails"
      title="同步详情"
      direction="rtl"
      size="400px"
    >
      <div class="sync-details">
        <el-timeline>
          <el-timeline-item
            v-for="log in syncLogs"
            :key="log.id"
            :timestamp="log.timestamp"
            :type="log.type"
          >
            {{ log.message }}
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fullDataSyncService } from '@/services/fullDataSync'

// 状态管理
const isSyncing = ref(false)
const isTriggering = ref(false)
const isIncrementalSyncing = ref(false)
const showDetails = ref(false)

const syncProgress = reactive({
  percentage: 0,
  currentEntity: '',
  currentPage: 0,
  totalPages: 0,
  isBackground: true,
  completedEntities: 0,
  totalEntities: 0
})

const syncLogs = ref([])

// 计算属性
const getSyncStatusText = () => {
  if (!isSyncing.value) return ''
  
  if (syncProgress.currentEntity) {
    return `正在同步 ${syncProgress.currentEntity}`
  }
  return '准备同步数据...'
}

const getSyncSubText = () => {
  if (!isSyncing.value) return ''
  
  const completed = syncProgress.completedEntities
  const total = syncProgress.totalEntities
  
  if (syncProgress.totalPages > 0) {
    return `第 ${syncProgress.currentPage}/${syncProgress.totalPages} 页 (${completed}/${total} 项完成)`
  }
  
  return `${completed}/${total} 项已完成`
}

// 方法
const triggerFullSync = async () => {
  try {
    isTriggering.value = true
    
    const { confirm } = await ElMessageBox.confirm(
      '这将清空本地数据并从云端重新下载所有数据，是否继续？',
      '全量同步确认',
      {
        confirmButtonText: '确认同步',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    if (!confirm) return
    
    await startFullSync(false) // 前台同步模式
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('启动同步失败')
    }
  } finally {
    isTriggering.value = false
  }
}

const triggerIncrementalSync = async () => {
  try {
    isIncrementalSyncing.value = true
    await startFullSync(true, true) // 后台增量同步
    ElMessage.success('增量同步已启动')
  } catch (error) {
    ElMessage.error('增量同步启动失败')
  } finally {
    isIncrementalSyncing.value = false
  }
}

const startFullSync = async (background = true, incrementalOnly = false) => {
  isSyncing.value = true
  resetProgress()
  
  addLog('开始数据同步', 'primary')
  
  try {
    // 注册回调
    fullDataSyncService.addCallback('progress', onSyncProgress)
    fullDataSyncService.addCallback('complete', onSyncComplete)
    fullDataSyncService.addCallback('error', onSyncError)
    fullDataSyncService.addCallback('entity_start', onEntityStart)
    fullDataSyncService.addCallback('entity_complete', onEntityComplete)
    
    // 启动同步
    const success = await fullDataSyncService.startFullSync(
      background,
      incrementalOnly
    )
    
    if (!success) {
      throw new Error('同步启动失败')
    }
    
  } catch (error) {
    addLog(`同步失败: ${error.message}`, 'danger')
    isSyncing.value = false
    throw error
  }
}

const cancelSync = () => {
  fullDataSyncService.cancelSync()
  isSyncing.value = false
  addLog('用户取消了同步', 'warning')
}

const resetProgress = () => {
  Object.assign(syncProgress, {
    percentage: 0,
    currentEntity: '',
    currentPage: 0,
    totalPages: 0,
    isBackground: true,
    completedEntities: 0,
    totalEntities: 5 // 根据实际实体数量调整
  })
}

const addLog = (message, type = 'info') => {
  syncLogs.value.unshift({
    id: Date.now(),
    message,
    type,
    timestamp: new Date().toLocaleTimeString()
  })
  
  // 保留最近50条日志
  if (syncLogs.value.length > 50) {
    syncLogs.value.pop()
  }
}

// 回调处理
const onSyncProgress = (progress) => {
  Object.assign(syncProgress, progress)
}

const onSyncComplete = () => {
  isSyncing.value = false
  addLog('数据同步完成!', 'success')
  ElMessage.success('云端数据已同步到本地')
  
  // 刷新相关组件
  window.dispatchEvent(new CustomEvent('data-sync-complete'))
}

const onSyncError = (error) => {
  isSyncing.value = false
  addLog(`同步错误: ${error}`, 'danger')
  ElMessage.error(`同步失败: ${error}`)
}

const onEntityStart = (entityType) => {
  addLog(`开始同步 ${entityType}`, 'primary')
}

const onEntityComplete = (entityType) => {
  addLog(`${entityType} 同步完成`, 'success')
}

// 生命周期
onMounted(() => {
  // 检查是否需要自动同步
  checkAutoSync()
})

onUnmounted(() => {
  // 清理回调
  fullDataSyncService.removeAllCallbacks()
})

// 自动同步检查
const checkAutoSync = async () => {
  // 检查本地存储是否为空
  const hasLocalData = await checkLocalDataExists()
  
  if (!hasLocalData) {
    // 首次使用或数据丢失，启动后台同步
    ElMessage.info('检测到本地无数据，正在后台同步云端数据...')
    await startFullSync(true, false) // 后台全量同步
  } else {
    // 检查是否需要增量同步
    const needsIncremental = await checkNeedsIncrementalSync()
    if (needsIncremental) {
      await startFullSync(true, true) // 后台增量同步
    }
  }
}

const checkLocalDataExists = async () => {
  try {
    const todos = await localStorage.getItem('todos')
    const lists = await localStorage.getItem('sharedLists')
    return !!(todos || lists)
  } catch {
    return false
  }
}

const checkNeedsIncrementalSync = async () => {
  // 检查上次同步时间
  const lastSync = localStorage.getItem('lastSyncTime')
  if (!lastSync) return true
  
  const lastSyncTime = new Date(lastSync)
  const now = new Date()
  const hoursSinceLastSync = (now - lastSyncTime) / (1000 * 60 * 60)
  
  // 超过24小时需要同步
  return hoursSinceLastSync > 24
}

// 暴露方法给父组件
defineExpose({
  triggerFullSync,
  triggerIncrementalSync,
  cancelSync,
  isSyncing: computed(() => isSyncing.value)
})
</script>

<style scoped>
.full-data-sync-manager {
  position: fixed;
  top: 70px;
  right: 20px;
  z-index: 1000;
}

.sync-indicator {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 20px;
  min-width: 280px;
  border: 2px solid #409eff;
  animation: pulse 2s infinite;
}

.sync-indicator.background-mode {
  border-color: #67c23a;
  animation: none;
}

@keyframes pulse {
  0% { box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); }
  50% { box-shadow: 0 6px 20px rgba(64, 158, 255, 0.3); }
  100% { box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); }
}

.indicator-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.indicator-text {
  flex: 1;
}

.main-text {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.sub-text {
  font-size: 12px;
  color: #909399;
}

.background-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 15px;
  padding: 8px 12px;
  background: #f0f9ff;
  border-radius: 6px;
  font-size: 12px;
  color: #409eff;
}

.manual-sync {
  display: flex;
  gap: 10px;
  background: white;
  padding: 10px 15px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.sync-details {
  padding: 20px 0;
}

.sync-details :deep(.el-timeline) {
  padding-left: 20px;
}

.sync-details :deep(.el-timeline-item__timestamp) {
  font-size: 12px;
  color: #909399;
}
</style>