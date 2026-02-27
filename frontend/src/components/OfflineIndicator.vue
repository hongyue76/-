<template>
  <div class="offline-indicator" :class="indicatorClasses">
    <div class="indicator-content">
      <el-badge :is-dot="true" :type="badgeType">
        <el-icon class="status-icon" :size="16">
          <component :is="statusIcon" />
        </el-icon>
      </el-badge>
      
      <span class="status-text">{{ statusText }}</span>
      
      <div v-if="showDetails" class="status-details">
        <el-popover
          placement="bottom"
          :width="250"
          trigger="hover"
        >
          <template #reference>
            <el-icon class="info-icon"><InfoFilled /></el-icon>
          </template>
          
          <div class="network-details">
            <div class="detail-item">
              <span class="label">网络状态:</span>
              <span class="value">{{ getNetworkProperty('online', false) ? '在线' : '离线' }}</span>
            </div>
            <div class="detail-item">
              <span class="label">服务器连接:</span>
              <span class="value">{{ getNetworkProperty('serverReachable', true) ? '正常' : '异常' }}</span>
            </div>
            <div class="detail-item">
              <span class="label">网络质量:</span>
              <el-progress 
                :percentage="networkQuality" 
                :stroke-width="8"
                :show-text="false"
                :color="qualityColor"
              />
              <span class="quality-text">{{ networkQuality }}%</span>
            </div>
            <div v-if="connectionType !== 'unknown'" class="detail-item">
              <span class="label">连接类型:</span>
              <span class="value">{{ getConnectionTypeName(connectionType) }}</span>
            </div>
            <div v-if="pendingSyncCount > 0" class="detail-item">
              <span class="label">待同步:</span>
              <span class="value warning">{{ pendingSyncCount }} 项</span>
            </div>
          </div>
        </el-popover>
      </div>
      
      <div v-if="!isOnline && showRetry" class="retry-section">
        <el-button 
          size="small" 
          type="primary" 
          @click="handleRetry"
          :loading="retrying"
        >
          重试连接
        </el-button>
      </div>
    </div>
    
    <!-- 离线提示条 -->
    <div v-if="!isOnline" class="offline-banner">
      <el-alert
        title="您当前处于离线状态"
        type="warning"
        description="应用将在本地保存您的更改，网络恢复后自动同步"
        show-icon
        closable
        @close="handleBannerClose"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useNetwork } from '../utils/networkMonitor'
import { useSync } from '../utils/syncService'
import { ElMessage } from 'element-plus'
import { 
  InfoFilled, 
  Connection, 
  Close,
  Warning, 
  SuccessFilled,
  Refresh 
} from '@element-plus/icons-vue'

const props = defineProps({
  showDetails: {
    type: Boolean,
    default: true
  },
  showRetry: {
    type: Boolean,
    default: true
  },
  autoHideBanner: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['status-change', 'retry'])

const networkComposable = useNetwork()
const isOnline = networkComposable.isOnline
const networkStatus = networkComposable.networkStatus
const getNetworkQualityScore = networkComposable.getNetworkQualityScore
const { forceSync, getSyncStatus } = useSync()

const retrying = ref(false)
const showBanner = ref(true)
const pendingSyncCount = ref(0)
const networkQuality = ref(0)

// 安全获取网络状态属性
const getNetworkProperty = (property, defaultValue = null) => {
  if (!networkStatus.value) return defaultValue
  return networkStatus.value[property] ?? defaultValue
}

// 计算属性
const indicatorClasses = computed(() => ({
  'online': isOnline.value && getNetworkProperty('serverReachable', true),
  'offline': !isOnline.value,
  'partial': isOnline.value && !getNetworkProperty('serverReachable', true),
  'poor-quality': networkQuality.value < 50
}))

const badgeType = computed(() => {
  if (!isOnline.value) return 'danger'
  if (!getNetworkProperty('serverReachable', true)) return 'warning'
  if (networkQuality.value < 50) return 'warning'
  return 'success'
})

const statusIcon = computed(() => {
  if (!isOnline.value) return Close
  if (!getNetworkProperty('serverReachable', true)) return Warning
  if (networkQuality.value < 50) return Warning
  return Connection
})

const statusText = computed(() => {
  if (!isOnline.value) return '离线模式'
  if (!getNetworkProperty('serverReachable', true)) return '服务器连接异常'
  if (networkQuality.value < 30) return '网络较差'
  if (networkQuality.value < 70) return '网络一般'
  return '网络良好'
})

const connectionType = computed(() => getNetworkProperty('type', 'unknown'))
const qualityColor = computed(() => {
  if (networkQuality.value < 30) return '#f56c6c'
  if (networkQuality.value < 70) return '#e6a23c'
  return '#67c23a'
})

// 方法
const getConnectionTypeName = (type) => {
  const names = {
    'slow-2g': '2G (慢速)',
    '2g': '2G',
    '3g': '3G',
    '4g': '4G',
    'unknown': '未知'
  }
  return names[type] || type.toUpperCase()
}

const handleRetry = async () => {
  retrying.value = true
  try {
    await forceSync()
    ElMessage.success('同步请求已发送')
    emit('retry')
  } catch (error) {
    ElMessage.error('同步失败: ' + error.message)
  } finally {
    retrying.value = false
  }
}

const handleBannerClose = () => {
  showBanner.value = false
  if (props.autoHideBanner) {
    localStorage.setItem('offlineBannerClosed', 'true')
  }
}

const updateSyncStatus = async () => {
  try {
    const status = await getSyncStatus()
    pendingSyncCount.value = status.pendingCount
  } catch (error) {
    console.error('获取同步状态失败:', error)
  }
}

const updateNetworkQuality = () => {
  networkQuality.value = getNetworkQualityScore()
}

// 生命周期
onMounted(() => {
  // 检查是否应该显示横幅
  if (props.autoHideBanner) {
    const closed = localStorage.getItem('offlineBannerClosed')
    showBanner.value = !closed && !isOnline.value
  } else {
    showBanner.value = !isOnline.value
  }
  
  // 定期更新状态
  const interval = setInterval(() => {
    updateSyncStatus()
    updateNetworkQuality()
  }, 5000)
  
  // 监听网络状态变化
  const networkListener = (event) => {
    emit('status-change', event)
    if (event.type === 'online') {
      showBanner.value = false
      if (props.autoHideBanner) {
        localStorage.removeItem('offlineBannerClosed')
      }
    } else if (event.type === 'offline') {
      showBanner.value = true
    }
  }
  
  useNetwork().addNetworkListener(networkListener)
  
  // 清理函数
  onUnmounted(() => {
    clearInterval(interval)
    useNetwork().removeNetworkListener(networkListener)
  })
  
  // 初始状态更新
  updateSyncStatus()
  updateNetworkQuality()
})
</script>

<style scoped>
.offline-indicator {
  position: fixed;
  top: 60px;
  right: 20px;
  z-index: 1000;
  transition: all 0.3s ease;
}

.indicator-content {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 20px;
  background: white;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  border: 1px solid #ebeef5;
}

.status-text {
  font-size: 12px;
  font-weight: 500;
  color: #606266;
}

.info-icon {
  color: #909399;
  cursor: pointer;
  transition: color 0.2s;
}

.info-icon:hover {
  color: #409eff;
}

.retry-section {
  margin-left: 8px;
}

.offline-banner {
  position: fixed;
  top: 110px;
  right: 20px;
  width: 350px;
  z-index: 999;
}

.network-details {
  font-size: 12px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.detail-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.label {
  color: #909399;
  margin-right: 8px;
}

.value {
  color: #606266;
  font-weight: 500;
}

.value.warning {
  color: #e6a23c;
}

.quality-text {
  margin-left: 8px;
  color: #606266;
  font-weight: 500;
}

/* 状态颜色 */
.offline-indicator.online .indicator-content {
  border-color: #67c23a;
}

.offline-indicator.online .status-text {
  color: #67c23a;
}

.offline-indicator.offline .indicator-content {
  border-color: #f56c6c;
}

.offline-indicator.offline .status-text {
  color: #f56c6c;
}

.offline-indicator.partial .indicator-content {
  border-color: #e6a23c;
}

.offline-indicator.partial .status-text {
  color: #e6a23c;
}

.offline-indicator.poor-quality .indicator-content {
  border-color: #e6a23c;
}

.offline-indicator.poor-quality .status-text {
  color: #e6a23c;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .offline-indicator {
    top: 50px;
    right: 10px;
  }
  
  .offline-banner {
    top: 100px;
    right: 10px;
    width: 300px;
  }
  
  .indicator-content {
    padding: 6px 10px;
  }
  
  .status-text {
    font-size: 11px;
  }
}
</style>