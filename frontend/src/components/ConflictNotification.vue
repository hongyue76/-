<template>
  <div class="conflict-notification" v-if="hasConflicts">
    <el-alert
      :title="`发现 ${conflictCount} 个冲突需要处理`"
      type="warning"
      show-icon
      closable
      @close="dismissNotification"
    >
      <template #default>
        <div class="conflict-summary">
          <el-button 
            type="primary" 
            size="small" 
            @click="openConflictDialog"
            round
          >
            立即处理
          </el-button>
          <span class="conflict-info">
            {{ getTimeInfo() }}
          </span>
        </div>
      </template>
    </el-alert>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useOfflineSync } from '@/composables/useOfflineSync'

const { conflicts, resolveConflict } = useOfflineSync()

const hasConflicts = computed(() => conflicts.value.length > 0)
const conflictCount = computed(() => conflicts.value.length)

const dismissNotification = () => {
  // 可以添加延时提醒逻辑
  console.log('冲突通知已关闭')
}

const openConflictDialog = () => {
  // 触发全局事件打开冲突处理对话框
  window.dispatchEvent(new CustomEvent('open-conflict-dialog'))
}

const getTimeInfo = () => {
  if (conflicts.value.length === 0) return ''
  
  const latestConflict = conflicts.value[0]
  const conflictTime = new Date(latestConflict.detected_at)
  const now = new Date()
  const minutesAgo = Math.floor((now - conflictTime) / 60000)
  
  return `${minutesAgo}分钟前检测到`
}
</script>

<style scoped>
.conflict-notification {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  max-width: 400px;
}

.conflict-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.conflict-info {
  font-size: 12px;
  color: #909399;
}
</style>