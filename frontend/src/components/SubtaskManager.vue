<template>
  <div class="subtask-manager">
    <!-- 子任务列表 -->
    <div v-if="subtasks.length > 0" class="subtasks-list">
      <div class="subtasks-header">
        <h4>子任务 ({{ subtasks.length }})</h4>
        <el-button 
          type="primary" 
          size="small" 
          @click="openAddSubtaskDialog"
          icon="Plus"
        >
          添加子任务
        </el-button>
      </div>
      
      <div class="subtasks-container">
        <el-collapse v-model="activeNames" accordion>
          <el-collapse-item 
            v-for="subtask in subtasks" 
            :key="subtask.id"
            :name="subtask.id.toString()"
          >
            <template #title>
              <div class="subtask-item-header">
                <el-checkbox 
                  v-model="subtask.completed"
                  @change="toggleSubtaskComplete(subtask)"
                  :disabled="!canEdit"
                />
                <span 
                  class="subtask-title"
                  :class="{ 'completed': subtask.completed }"
                >
                  {{ subtask.title }}
                </span>
                <el-tag 
                  :type="getPriorityType(subtask.priority)"
                  size="small"
                  effect="plain"
                >
                  {{ subtask.priority }}
                </el-tag>
                <div class="subtask-actions">
                  <el-button 
                    v-if="canEdit"
                    type="primary" 
                    link 
                    size="small"
                    @click.stop="editSubtask(subtask)"
                    icon="Edit"
                  >
                    编辑
                  </el-button>
                  <el-button 
                    v-if="canEdit"
                    type="danger" 
                    link 
                    size="small"
                    @click.stop="deleteSubtask(subtask)"
                    icon="Delete"
                  >
                    删除
                  </el-button>
                </div>
              </div>
            </template>
            
            <div class="subtask-details">
              <div v-if="subtask.description" class="subtask-description">
                <strong>描述:</strong> {{ subtask.description }}
              </div>
              
              <div class="subtask-meta">
                <div v-if="subtask.due_date" class="due-date">
                  <el-icon><Calendar /></el-icon>
                  <span>截止日期: {{ formatDate(subtask.due_date) }}</span>
                </div>
                
                <div class="created-at">
                  <el-icon><Clock /></el-icon>
                  <span>创建时间: {{ formatDate(subtask.created_at) }}</span>
                </div>
              </div>
              
              <!-- 嵌套子任务 -->
              <SubtaskManager 
                v-if="subtask.children_count > 0"
                :parent-id="subtask.id"
                :can-edit="canEdit"
                @subtask-updated="$emit('subtask-updated')"
              />
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="empty-subtasks">
      <el-empty 
        description="暂无子任务"
        :image-size="80"
      >
        <el-button 
          v-if="canEdit"
          type="primary" 
          @click="openAddSubtaskDialog"
        >
          添加第一个子任务
        </el-button>
      </el-empty>
    </div>
    
    <!-- 添加/编辑子任务对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingSubtask ? '编辑子任务' : '添加子任务'"
      width="500px"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
      >
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="form.title"
            placeholder="请输入子任务标题"
          />
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入子任务描述（可选）"
          />
        </el-form-item>
        
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="form.priority" placeholder="请选择优先级">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="截止日期" prop="due_date">
          <el-date-picker
            v-model="form.due_date"
            type="datetime"
            placeholder="选择截止日期"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button 
            type="primary" 
            @click="submitForm"
            :loading="submitting"
          >
            {{ editingSubtask ? '更新' : '创建' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Calendar, Clock, Plus, Edit, Delete } from '@element-plus/icons-vue'
import api from '../utils/api'

const props = defineProps({
  parentId: {
    type: Number,
    required: true
  },
  canEdit: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['subtask-updated'])

const subtasks = ref([])
const activeNames = ref([])
const dialogVisible = ref(false)
const editingSubtask = ref(null)
const submitting = ref(false)
const formRef = ref()

const form = reactive({
  title: '',
  description: '',
  priority: 'medium',
  due_date: null
})

const rules = {
  title: [
    { required: true, message: '请输入子任务标题', trigger: 'blur' },
    { min: 1, max: 200, message: '标题长度应在1-200个字符之间', trigger: 'blur' }
  ]
}

// 获取优先级类型
const getPriorityType = (priority) => {
  const types = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'success'
  }
  return types[priority] || 'info'
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN')
}

// 加载子任务
const loadSubtasks = async () => {
  try {
    const response = await api.get(`/todos/${props.parentId}/children`)
    subtasks.value = response.data
  } catch (error) {
    console.error('加载子任务失败:', error)
    ElMessage.error('加载子任务失败')
  }
}

// 切换子任务完成状态
const toggleSubtaskComplete = async (subtask) => {
  try {
    await api.put(`/todos/${subtask.id}`, {
      completed: subtask.completed
    })
    ElMessage.success('更新成功')
    emit('subtask-updated')
  } catch (error) {
    console.error('更新子任务失败:', error)
    ElMessage.error('更新失败')
    // 恢复原来的状态
    subtask.completed = !subtask.completed
  }
}

// 打开添加子任务对话框
const openAddSubtaskDialog = () => {
  editingSubtask.value = null
  resetForm()
  dialogVisible.value = true
}

// 编辑子任务
const editSubtask = (subtask) => {
  editingSubtask.value = subtask
  form.title = subtask.title
  form.description = subtask.description || ''
  form.priority = subtask.priority
  form.due_date = subtask.due_date
  dialogVisible.value = true
}

// 删除子任务
const deleteSubtask = async (subtask) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除子任务 "${subtask.title}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await api.delete(`/todos/${subtask.id}/cascade`)
    ElMessage.success('删除成功')
    await loadSubtasks()
    emit('subtask-updated')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除子任务失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 提交表单
const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        let response
        if (editingSubtask.value) {
          // 编辑现有子任务
          response = await api.put(`/todos/${editingSubtask.value.id}`, form)
          ElMessage.success('更新成功')
        } else {
          // 创建新子任务
          response = await api.post(`/todos/${props.parentId}/children`, form)
          ElMessage.success('创建成功')
        }
        
        dialogVisible.value = false
        await loadSubtasks()
        emit('subtask-updated')
      } catch (error) {
        console.error('操作失败:', error)
        ElMessage.error(error.response?.data?.detail || '操作失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

// 重置表单
const resetForm = () => {
  form.title = ''
  form.description = ''
  form.priority = 'medium'
  form.due_date = null
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

// 生命周期
onMounted(() => {
  loadSubtasks()
})
</script>

<style scoped>
.subtask-manager {
  margin: 15px 0;
}

.subtasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.subtasks-header h4 {
  margin: 0;
  color: #606266;
}

.subtask-item-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.subtask-title {
  flex: 1;
  font-weight: 500;
}

.subtask-title.completed {
  text-decoration: line-through;
  color: #909399;
}

.subtask-actions {
  display: flex;
  gap: 8px;
}

.subtask-details {
  padding: 15px 0;
}

.subtask-description {
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  color: #606266;
}

.subtask-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.subtask-meta div {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #909399;
  font-size: 12px;
}

.empty-subtasks {
  text-align: center;
  padding: 30px 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>