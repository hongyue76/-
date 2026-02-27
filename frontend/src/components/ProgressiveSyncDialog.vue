<template>
  <div class="progressive-sync" v-if="isVisible">
    <div class="sync-overlay" @click="handleOverlayClick">
      <div class="sync-dialog" @click.stop>
        <!-- 同步头部 -->
        <div class="sync-header">
          <el-icon class="sync-icon" :class="syncStatus">
            <Loading v-if="syncStatus === 'syncing'" />
            <Check v-if="syncStatus === 'completed'" />
            <CircleClose v-if="syncStatus === 'error'" />
          </el-icon>
          <div class="sync-title">
            <h3>{{ getTitle() }}</h3>
            <p class="sync-subtitle">{{ getSubtitle() }}</p>
          </div>
          <el-button 
            v-if="syncStatus !== 'syncing'" 
            circle 
            @click="closeDialog"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>

        <!-- 进度显示 -->
        <div class="sync-progress-area" v-if="syncStatus === 'syncing'">
          <!-- 主进度条 -->
          <div class="main-progress">
            <div class="progress-label">
              <span>整体进度</span>
              <span>{{ Math.round(progressData.overallPercentage) }}%</span>
            </div>
            <el-progress 
              :percentage="progressData.overallPercentage"
              :stroke-width="12"
              striped
              striped-flow
              :duration="2"
              status="success"
            />
          </div>

          <!-- 批次进度 -->
          <div class="batch-progress" v-if="progressData.currentBatch > 0">
            <div class="batch-info">
              <span>批次 {{ progressData.currentBatch }}/{{ progressData.totalBatches }}</span>
              <span>{{ progressData.batchItemsProcessed }}/{{ progressData.currentBatchSize }} 项</span>
            </div>
            <el-progress 
              :percentage="getBatchPercentage()"
              :stroke-width="6"
              :show-text="false"
            />
          </div>

          <!-- 速度和时间估算 -->
          <div class="sync-stats" v-if="progressData.speed">
            <div class="stat-item">
              <el-icon><Speed /></el-icon>
              <span>{{ progressData.speed.toFixed(1) }} 项/秒</span>
            </div>
            <div class="stat-item" v-if="progressData.estimatedTime">
              <el-icon><Timer /></el-icon>
              <span>剩余约 {{ formatTime(progressData.estimatedTime) }}</span>
            </div>
          </div>
        </div>

        <!-- 详细列表 -->
        <div class="sync-details" v-if="showDetails">
          <el-tabs v-model="activeTab">
            <el-tab-pane label="同步详情" name="details">
              <div class="details-list">
                <div 
                  v-for="item in syncItems" 
                  :key="item.id"
                  class="sync-item"
                  :class="getItemStatusClass(item)"
                >
                  <div class="item-info">
                    <el-icon class="item-icon">
                      <Document v-if="item.type === 'task'" />
                      <Comment v-if="item.type === 'comment'" />
                      <User v-if="item.type === 'user'" />
                    </el-icon>
                    <div class="item-text">
                      <div class="item-title">{{ item.title }}</div>
                      <div class="item-description">{{ item.description }}</div>
                    </div>
                  </div>
                  <div class="item-status">
                    <el-tag :type="getItemStatusType(item.status)">
                      {{ getItemStatusText(item.status) }}
                    </el-tag>
                  </div>
                </div>
              </div>
            </el-tab-pane>
            
            <el-tab-pane label="错误日志" name="errors" v-if="errorItems.length > 0">
              <div class="error-list">
                <div 
                  v-for="error in errorItems" 
                  :key="error.id"
                  class="error-item"
                >
                  <el-alert 
                    :title="error.title"
                    :description="error.message"
                    type="error"
                    show-icon
                    closable
                  />
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- 底部操作 -->
        <div class="sync-footer" v-if="syncStatus !== 'syncing'">
          <el-button @click="retrySync" v-if="syncStatus === 'error'">
            重试同步
          </el-button>
          <el-button type="primary" @click="closeDialog">
            {{ syncStatus === 'completed' ? '完成' : '关闭' }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: Boolean,
  syncService: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'complete', 'error'])

// 状态数据
const isVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const syncStatus = ref('syncing') // syncing, completed, error
const activeTab = ref('details')
const showDetails = ref(true)

// 进度数据
const progressData = ref({
  overallPercentage: 0,
  currentBatch: 0,
  totalBatches: 0,
  batchItemsProcessed: 0,
  currentBatchSize: 0,
  totalItems: 0,
  completedItems: 0,
  speed: 0,
  estimatedTime: 0
})

// 同步项目和错误
const syncItems = ref([])
const errorItems = ref([])

// 方法
const getTitle = () => {
  const titles = {
    'syncing': '正在同步数据',
    'completed': '同步完成',
    'error': '同步遇到问题'
  }
  return titles[syncStatus.value] || '数据同步'
}

const getSubtitle = () => {
  switch (syncStatus.value) {
    case 'syncing':
      return '请耐心等待，这可能需要一些时间...'
    case 'completed':
      return '所有数据已成功同步到本地'
    case 'error':
      return '部分数据同步失败，请查看错误详情'
    default:
      return ''
  }
}

const getBatchPercentage = () => {
  if (progressData.value.currentBatchSize === 0) return 0
  return (progressData.value.batchItemsProcessed / progressData.value.currentBatchSize) * 100
}

const formatTime = (seconds) => {
  if (seconds < 60) return `${Math.round(seconds)}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒`
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}小时${minutes}分`
}

const getItemStatusClass = (item) => {
  return {
    'item-pending': item.status === 'pending',
    'item-processing': item.status === 'processing',
    'item-completed': item.status === 'completed',
    'item-error': item.status === 'error'
  }
}

const getItemStatusType = (status) => {
  const typeMap = {
    'pending': 'info',
    'processing': 'warning',
    'completed': 'success',
    'error': 'danger'
  }
  return typeMap[status] || 'info'
}

const getItemStatusText = (status) => {
  const textMap = {
    'pending': '等待中',
    'processing': '处理中',
    'completed': '已完成',
    'error': '错误'
  }
  return textMap[status] || status
}

const handleOverlayClick = () => {
  // 点击遮罩层不关闭，除非同步完成或出错
  if (syncStatus.value !== 'syncing') {
    closeDialog()
  }
}

const closeDialog = () => {
  isVisible.value = false
  if (syncStatus.value === 'completed') {
    emit('complete')
  } else if (syncStatus.value === 'error') {
    emit('error')
  }
}

const retrySync = () => {
  // 重试逻辑
  syncStatus.value = 'syncing'
  errorItems.value = []
  // 调用实际的重试方法
  props.syncService.retry()
}

// 监听同步服务事件
const setupSyncListeners = () => {
  if (!props.syncService) return

  props.syncService.on('progress', (progress) => {
    progressData.value = {
      overallPercentage: progress.percentage,
      currentBatch: progress.current_batch,
      totalBatches: progress.total_batches,
      batchItemsProcessed: progress.batch_processed || 0,
      currentBatchSize: progress.batch_size || 0,
      totalItems: progress.total_items,
      completedItems: progress.completed_items,
      speed: progress.speed || 0,
      estimatedTime: progress.estimated_time || 0
    }
  })

  props.syncService.on('item-start', (item) => {
    const existingIndex = syncItems.value.findIndex(i => i.id === item.id)
    if (existingIndex >= 0) {
      syncItems.value[existingIndex].status = 'processing'
    } else {
      syncItems.value.push({
        ...item,
        status: 'processing'
      })
    }
  })

  props.syncService.on('item-complete', (item) => {
    const index = syncItems.value.findIndex(i => i.id === item.id)
    if (index >= 0) {
      syncItems.value[index].status = 'completed'
    }
  })

  props.syncService.on('item-error', (error) => {
    errorItems.value.push(error)
    
    const itemIndex = syncItems.value.findIndex(i => i.id === error.itemId)
    if (itemIndex >= 0) {
      syncItems.value[itemIndex].status = 'error'
    }
  })

  props.syncService.on('complete', () => {
    syncStatus.value = 'completed'
    ElMessage.success('数据同步完成')
  })

  props.syncService.on('error', (errorMessage) => {
    syncStatus.value = 'error'
    ElMessage.error(`同步失败: ${errorMessage}`)
  })
}

// 生命周期
onMounted(() => {
  setupSyncListeners()
})

onUnmounted(() => {
  // 清理监听器
  if (props.syncService && props.syncService.removeAllListeners) {
    props.syncService.removeAllListeners()
  }
})
</script>

<style scoped>
.progressive-sync {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2000;
}

.sync-overlay {
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.sync-dialog {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
}

.sync-header {
  display: flex;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #ebeef5;
}

.sync-icon {
  font-size: 24px;
  margin-right: 15px;
}

.sync-icon.syncing {
  color: #409eff;
  animation: rotate 2s linear infinite;
}

.sync-icon.completed {
  color: #67c23a;
}

.sync-icon.error {
  color: #f56c6c;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.sync-title {
  flex: 1;
}

.sync-title h3 {
  margin: 0 0 5px 0;
  color: #303133;
  font-size: 18px;
}

.sync-subtitle {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.sync-progress-area {
  padding: 20px;
}

.main-progress {
  margin-bottom: 20px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 14px;
  color: #606266;
}

.batch-progress {
  margin-bottom: 15px;
}

.batch-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
  color: #909399;
}

.sync-stats {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: #909399;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.sync-details {
  flex: 1;
  overflow-y: auto;
  border-top: 1px solid #ebeef5;
}

.details-list {
  padding: 15px;
}

.sync-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 10px;
  border-radius: 6px;
  border: 1px solid #ebeef5;
  transition: all 0.3s;
}

.sync-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.item-info {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 12px;
}

.item-icon {
  font-size: 18px;
  color: #409eff;
}

.item-text {
  display: flex;
  flex-direction: column;
}

.item-title {
  font-weight: 500;
  color: #303133;
  font-size: 14px;
}

.item-description {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.item-status {
  flex-shrink: 0;
}

.error-list {
  padding: 15px;
}

.error-item {
  margin-bottom: 10px;
}

.sync-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 15px 20px;
  border-top: 1px solid #ebeef5;
  background: #fafafa;
}
</style>