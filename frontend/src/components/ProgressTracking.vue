<template>
  <div class="progress-tracking">
    <!-- 进度更新表单 -->
    <el-card class="progress-update-card" v-if="canUpdateProgress">
      <template #header>
        <div class="card-header">
          <span>更新任务进度</span>
        </div>
      </template>
      
      <el-form
        :model="progressForm"
        :rules="progressRules"
        ref="progressFormRef"
        label-width="100px"
      >
        <el-form-item label="进度状态" prop="status">
          <el-select v-model="progressForm.status" style="width: 100%">
            <el-option label="待开始" value="todo" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="审核中" value="review" />
            <el-option label="已完成" value="done" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="完成百分比" prop="progress_percentage">
          <el-slider
            v-model="progressForm.progress_percentage"
            :min="0"
            :max="100"
            show-input
          />
        </el-form-item>
        
        <el-form-item label="花费时间" prop="hours_spent">
          <el-input-number
            v-model="progressForm.hours_spent"
            :min="0"
            controls-position="right"
          >
            <template #suffix>小时</template>
          </el-input-number>
        </el-form-item>
        
        <el-form-item label="进度说明" prop="notes">
          <el-input
            v-model="progressForm.notes"
            type="textarea"
            :rows="3"
            placeholder="请输入进度说明"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            @click="submitProgress"
            :loading="submitLoading"
          >
            更新进度
          </el-button>
          <el-button @click="resetProgressForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 进度历史记录 -->
    <el-card class="progress-history-card" v-if="progressTracks.length > 0">
      <template #header>
        <div class="card-header">
          <span>进度历史</span>
          <el-button 
            type="primary" 
            size="small" 
            @click="loadProgressTracks"
            :loading="loading"
          >
            刷新
          </el-button>
        </div>
      </template>
      
      <el-timeline>
        <el-timeline-item
          v-for="track in progressTracks"
          :key="track.id"
          :timestamp="formatDateTime(track.created_at)"
          placement="top"
        >
          <el-card>
            <h4>
              <el-tag :type="getStatusType(track.status)">
                {{ getStatusText(track.status) }}
              </el-tag>
              <span style="margin-left: 10px;">
                进度: {{ track.progress_percentage }}%
              </span>
            </h4>
            <p v-if="track.notes">{{ track.notes }}</p>
            <div class="track-meta">
              <span>更新人: {{ track.user.username }}</span>
              <span v-if="track.hours_spent > 0">花费时间: {{ track.hours_spent }}小时</span>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>
    
    <!-- 进度统计 -->
    <el-card class="progress-stats-card" v-if="progressStats">
      <template #header>
        <div class="card-header">
          <span>进度统计</span>
        </div>
      </template>
      
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-value">{{ progressStats.total }}</div>
          <div class="stat-label">总任务数</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #409eff;">{{ progressStats.todo }}</div>
          <div class="stat-label">待开始</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #e6a23c;">{{ progressStats.in_progress }}</div>
          <div class="stat-label">进行中</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #67c23a;">{{ progressStats.done }}</div>
          <div class="stat-label">已完成</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #909399;">{{ progressStats.review }}</div>
          <div class="stat-label">审核中</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #f56c6c;">{{ progressStats.completion_rate }}%</div>
          <div class="stat-label">完成率</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/api'

const props = defineProps({
  todoId: {
    type: Number,
    required: true
  },
  currentUser: {
    type: Object,
    required: true
  },
  canUpdateProgress: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['progress-updated'])

const loading = ref(false)
const submitLoading = ref(false)
const progressTracks = ref([])
const progressStats = ref(null)

const progressForm = ref({
  status: 'todo',
  progress_percentage: 0,
  hours_spent: 0,
  notes: ''
})

const progressRules = {
  status: [
    { required: true, message: '请选择进度状态', trigger: 'change' }
  ],
  progress_percentage: [
    { required: true, message: '请输入完成百分比', trigger: 'blur' }
  ]
}

const progressFormRef = ref()

// 计算属性
const latestProgress = computed(() => {
  return progressTracks.value.length > 0 ? progressTracks.value[0] : null
})

// 方法
const getStatusType = (status) => {
  const statusMap = {
    'todo': 'info',
    'in_progress': 'warning',
    'review': 'primary',
    'done': 'success'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status) => {
  const statusMap = {
    'todo': '待开始',
    'in_progress': '进行中',
    'review': '审核中',
    'done': '已完成'
  }
  return statusMap[status] || status
}

const formatDateTime = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN')
}

const loadProgressTracks = async () => {
  if (!props.todoId) return
  
  loading.value = true
  try {
    const response = await api.get(`/progress/todo/${props.todoId}`)
    progressTracks.value = response.data
    
    // 如果有进度记录，用最新的填充表单
    if (progressTracks.value.length > 0) {
      const latest = progressTracks.value[0]
      progressForm.value = {
        status: latest.status,
        progress_percentage: latest.progress_percentage,
        hours_spent: latest.hours_spent,
        notes: latest.notes || ''
      }
    }
    
    emit('progress-updated', progressTracks.value)
  } catch (error) {
    console.error('加载进度记录失败:', error)
  } finally {
    loading.value = false
  }
}

const loadProgressStats = async () => {
  // 这里应该调用获取团队进度统计的API
  // 暂时使用模拟数据
  progressStats.value = {
    total: 10,
    todo: 2,
    in_progress: 5,
    review: 1,
    done: 2,
    completion_rate: 20
  }
}

const submitProgress = async () => {
  if (!progressFormRef.value) return
  
  await progressFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitLoading.value = true
    try {
      const response = await api.post('/progress', {
        todo_id: props.todoId,
        status: progressForm.value.status,
        progress_percentage: progressForm.value.progress_percentage,
        hours_spent: progressForm.value.hours_spent,
        notes: progressForm.value.notes
      })
      
      ElMessage.success('进度更新成功')
      await loadProgressTracks()
      emit('progress-updated', progressTracks.value)
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '更新失败')
    } finally {
      submitLoading.value = false
    }
  })
}

const resetProgressForm = () => {
  if (progressFormRef.value) {
    progressFormRef.value.resetFields()
  }
  progressForm.value = {
    status: 'todo',
    progress_percentage: 0,
    hours_spent: 0,
    notes: ''
  }
}

// 监听todoId变化
watch(() => props.todoId, (newTodoId) => {
  if (newTodoId) {
    loadProgressTracks()
    loadProgressStats()
  }
})

// 生命周期
onMounted(() => {
  if (props.todoId) {
    loadProgressTracks()
    loadProgressStats()
  }
})

// 暴露方法给父组件
defineExpose({
  loadProgressTracks,
  loadProgressStats
})
</script>

<style scoped>
.progress-tracking {
  margin-top: 20px;
}

.progress-update-card,
.progress-history-card,
.progress-stats-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.track-meta {
  display: flex;
  gap: 20px;
  margin-top: 10px;
  font-size: 12px;
  color: #999;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 20px;
  text-align: center;
}

.stat-item {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

:deep(.el-timeline-item__timestamp) {
  color: #999;
  font-size: 12px;
}
</style>