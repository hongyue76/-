<template>
  <el-dialog
    v-model="dialogVisible"
    title="冲突处理中心"
    width="800px"
    :before-close="handleClose"
    class="conflict-dialog"
  >
    <div class="conflict-content">
      <!-- 冲突概览 -->
      <div class="conflict-overview">
        <el-statistic title="待处理冲突" :value="conflicts.length" />
        <el-statistic title="涉及任务" :value="uniqueTasks.size" />
        <el-statistic title="最早冲突" :value="earliestConflictTime" />
      </div>

      <!-- 冲突列表 -->
      <div class="conflict-list">
        <el-tabs v-model="activeTab" type="card">
          <el-tab-pane 
            v-for="(group, taskId) in conflictsByTask" 
            :key="taskId"
            :label="`任务 #${taskId} (${group.length})`"
            :name="taskId"
          >
            <ConflictDetailCard 
              v-for="conflict in group"
              :key="conflict.id"
              :conflict="conflict"
              @resolve="handleResolve"
              @preview="previewConflict"
            />
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 批量操作 -->
      <div class="batch-actions" v-if="conflicts.length > 1">
        <el-divider>批量处理</el-divider>
        <div class="batch-buttons">
          <el-button @click="batchResolve('server_wins')">全部采用服务器版本</el-button>
          <el-button @click="batchResolve('client_wins')">全部采用本地版本</el-button>
          <el-button @click="batchResolve('smart_merge')">全部智能合并</el-button>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">暂不处理</el-button>
        <el-button 
          type="primary" 
          @click="handleApplyAll"
          :disabled="pendingResolutions.size === 0"
        >
          应用所选解决方案 ({{ pendingResolutions.size }})
        </el-button>
      </div>
    </template>
  </el-dialog>

  <!-- 冲突预览抽屉 -->
  <el-drawer
    v-model="previewDrawer"
    title="冲突详情预览"
    direction="rtl"
    size="50%"
  >
    <ConflictPreview 
      v-if="selectedConflict"
      :conflict="selectedConflict"
    />
  </el-drawer>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import ConflictDetailCard from './ConflictDetailCard.vue'
import ConflictPreview from './ConflictPreview.vue'
import { useOfflineSync } from '@/composables/useOfflineSync'

const { conflicts, resolveConflict } = useOfflineSync()

const dialogVisible = ref(false)
const activeTab = ref('')
const previewDrawer = ref(false)
const selectedConflict = ref(null)
const pendingResolutions = ref(new Map())

// 计算属性
const conflictsByTask = computed(() => {
  const groups = {}
  conflicts.value.forEach(conflict => {
    const taskId = conflict.todo_id
    if (!groups[taskId]) {
      groups[taskId] = []
    }
    groups[taskId].push(conflict)
  })
  return groups
})

const uniqueTasks = computed(() => {
  return new Set(conflicts.value.map(c => c.todo_id))
})

const earliestConflictTime = computed(() => {
  if (conflicts.value.length === 0) return '无'
  const earliest = Math.min(...conflicts.value.map(c => new Date(c.detected_at)))
  return new Date(earliest).toLocaleString()
})

// 方法
const handleOpen = () => {
  dialogVisible.value = true
  if (Object.keys(conflictsByTask.value).length > 0) {
    activeTab.value = Object.keys(conflictsByTask.value)[0]
  }
}

const handleClose = () => {
  dialogVisible.value = false
  pendingResolutions.value.clear()
}

const handleResolve = (conflictId, resolution) => {
  pendingResolutions.value.set(conflictId, resolution)
}

const handleApplyAll = async () => {
  try {
    for (const [conflictId, resolution] of pendingResolutions.value) {
      await resolveConflict(conflictId, resolution)
    }
    ElMessage.success(`成功处理 ${pendingResolutions.value.size} 个冲突`)
    pendingResolutions.value.clear()
    handleClose()
  } catch (error) {
    ElMessage.error('处理冲突时发生错误')
  }
}

const batchResolve = (strategy) => {
  conflicts.value.forEach(conflict => {
    pendingResolutions.value.set(conflict.id, {
      type: strategy,
      data: null
    })
  })
  ElMessage.info(`已为 ${conflicts.value.length} 个冲突选择 ${strategy} 策略`)
}

const previewConflict = (conflict) => {
  selectedConflict.value = conflict
  previewDrawer.value = true
}

// 事件监听
onMounted(() => {
  window.addEventListener('open-conflict-dialog', handleOpen)
})

onUnmounted(() => {
  window.removeEventListener('open-conflict-dialog', handleOpen)
})
</script>

<style scoped>
.conflict-dialog :deep(.el-dialog__body) {
  padding: 20px;
}

.conflict-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.conflict-overview {
  display: flex;
  gap: 30px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.conflict-list {
  flex: 1;
}

.batch-actions {
  background: #fafafa;
  padding: 15px;
  border-radius: 8px;
}

.batch-buttons {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
}
</style>