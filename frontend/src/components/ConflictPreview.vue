<template>
  <div class="conflict-preview">
    <div class="preview-header">
      <h3>冲突详情预览</h3>
      <el-tag :type="getStatusType()" size="small">
        {{ getStatusText() }}
      </el-tag>
    </div>

    <!-- 任务基本信息 -->
    <el-card class="task-info" shadow="never">
      <template #header>
        <div class="card-header">
          <span>任务信息</span>
          <el-button 
            type="primary" 
            size="small" 
            @click="viewTaskDetail"
          >
            查看完整任务
          </el-button>
        </div>
      </template>
      
      <el-descriptions :column="1" size="small">
        <el-descriptions-item label="任务ID">
          #{{ conflict.todo_id }}
        </el-descriptions-item>
        <el-descriptions-item label="检测时间">
          {{ formatDateTime(conflict.detected_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="冲突字段">
          <el-tag size="small">{{ getFieldDisplayName(conflict.field_name) }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 详细对比视图 -->
    <el-card class="comparison-view" shadow="never">
      <template #header>
        <span>详细对比</span>
      </template>
      
      <div class="comparison-table">
        <div class="comparison-row header-row">
          <div class="cell">属性</div>
          <div class="cell server-cell">服务器版本</div>
          <div class="cell client-cell">您的版本</div>
        </div>
        
        <div class="comparison-row">
          <div class="cell label-cell">值</div>
          <div class="cell server-cell">
            <ConflictValueDisplay 
              :value="conflict.server_value" 
              :field-type="conflict.field_name"
              variant="server"
              size="normal"
            />
          </div>
          <div class="cell client-cell">
            <ConflictValueDisplay 
              :value="conflict.client_new_value" 
              :field-type="conflict.field_name"
              variant="client"
              size="normal"
            />
          </div>
        </div>
        
        <div class="comparison-row">
          <div class="cell label-cell">时间戳</div>
          <div class="cell server-cell">
            {{ formatDateTime(conflict.server_timestamp) }}
          </div>
          <div class="cell client-cell">
            {{ formatDateTime(conflict.client_timestamp) }}
          </div>
        </div>
        
        <div class="comparison-row">
          <div class="cell label-cell">原始值</div>
          <div class="cell server-cell">
            <em>无</em>
          </div>
          <div class="cell client-cell">
            <ConflictValueDisplay 
              :value="conflict.client_old_value" 
              :field-type="conflict.field_name"
              size="small"
            />
          </div>
        </div>
      </div>
    </el-card>

    <!-- 影响分析 -->
    <el-card class="impact-analysis" shadow="never">
      <template #header>
        <span>影响分析</span>
      </template>
      
      <div class="analysis-content">
        <el-alert 
          v-if="hasDependencies" 
          type="warning" 
          show-icon
          title="依赖关系提醒"
        >
          <template #default>
            此任务被 {{ dependencyCount }} 个子任务依赖，修改可能影响下游任务
          </template>
        </el-alert>
        
        <el-alert 
          v-if="hasAssignments" 
          type="info" 
          show-icon
          title="协作提醒"
        >
          <template #default>
            此任务已分配给 {{ assigneeCount }} 位协作者，请谨慎修改
          </template>
        </el-alert>
        
        <div class="statistics">
          <el-statistic title="冲突严重程度" :value="getSeverityScore()" suffix="/100" />
          <el-statistic title="解决建议" :value="getRecommendation()" />
        </div>
      </div>
    </el-card>

    <!-- 快速操作 -->
    <div class="quick-actions">
      <el-button 
        type="primary" 
        @click="goToFullResolver"
        size="large"
        style="width: 100%"
      >
        在冲突中心中详细处理
      </el-button>
      
      <div class="quick-resolve-buttons">
        <el-button @click="quickResolve('server_wins')">采用服务器版本</el-button>
        <el-button @click="quickResolve('client_wins')">保留我的修改</el-button>
        <el-button 
          v-if="canSmartMerge" 
          type="success" 
          @click="quickResolve('smart_merge')"
        >
          智能合并
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import ConflictValueDisplay from './ConflictValueDisplay.vue'

const props = defineProps({
  conflict: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['resolve', 'close'])

const router = useRouter()

// 计算属性
const hasDependencies = computed(() => {
  // 模拟数据，实际应从API获取
  return props.conflict.todo_id % 3 === 0
})

const dependencyCount = computed(() => hasDependencies.value ? 3 : 0)

const hasAssignments = computed(() => {
  return props.conflict.todo_id % 2 === 0
})

const assigneeCount = computed(() => hasAssignments.value ? 2 : 0)

const canSmartMerge = computed(() => {
  const mergeableFields = ['title', 'description', 'content']
  return mergeableFields.includes(props.conflict.field_name)
})

// 方法
const getStatusType = () => {
  if (props.conflict.resolved) return 'success'
  return 'warning'
}

const getStatusText = () => {
  if (props.conflict.resolved) return '已解决'
  return '待处理'
}

const getFieldDisplayName = (fieldName) => {
  const map = {
    'title': '标题',
    'description': '描述',
    'priority': '优先级',
    'completed': '完成状态',
    'due_date': '截止日期'
  }
  return map[fieldName] || fieldName
}

const formatDateTime = (timestamp) => {
  if (!timestamp) return '未知'
  return new Date(timestamp).toLocaleString('zh-CN')
}

const getSeverityScore = () => {
  // 简化的严重程度计算
  let score = 30 // 基础分数
  
  if (hasDependencies.value) score += 30
  if (hasAssignments.value) score += 20
  if (props.conflict.field_name === 'title') score += 20
  
  return Math.min(score, 100)
}

const getRecommendation = () => {
  const severity = getSeverityScore()
  if (severity > 80) return '建议人工审核'
  if (severity > 50) return '可考虑合并'
  return '可自动处理'
}

const viewTaskDetail = () => {
  router.push(`/todos/${props.conflict.todo_id}`)
  emit('close')
}

const goToFullResolver = () => {
  window.dispatchEvent(new CustomEvent('open-conflict-dialog'))
  emit('close')
}

const quickResolve = (strategy) => {
  const resolution = {
    type: strategy,
    data: strategy === 'smart_merge' ? { 
      merged: `${props.conflict.server_value} & ${props.conflict.client_new_value}` 
    } : null
  }
  emit('resolve', props.conflict.id, resolution)
  emit('close')
}
</script>

<style scoped>
.conflict-preview {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.task-info :deep(.card-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
}

.comparison-row {
  display: grid;
  grid-template-columns: 120px 1fr 1fr;
  border-bottom: 1px solid #ebeef5;
}

.comparison-row.header-row {
  background: #f5f7fa;
  font-weight: bold;
}

.cell {
  padding: 12px;
  border-right: 1px solid #ebeef5;
}

.cell:last-child {
  border-right: none;
}

.label-cell {
  background: #fafafa;
  font-weight: 500;
}

.server-cell {
  background: #f0f7ff;
}

.client-cell {
  background: #fff7f0;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.statistics {
  display: flex;
  gap: 30px;
  justify-content: center;
}

.quick-actions {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.quick-resolve-buttons {
  display: flex;
  gap: 10px;
  justify-content: center;
}
</style>