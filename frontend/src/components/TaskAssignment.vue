<template>
  <div class="task-assignment">
    <el-dialog
      v-model="dialogVisible"
      :title="editingAssignment ? '编辑任务分配' : '分配任务'"
      width="500px"
      @close="resetForm"
    >
      <el-form
        :model="form"
        :rules="rules"
        ref="formRef"
        label-width="100px"
      >
        <el-form-item label="选择用户" prop="assignee_id">
          <el-select
            v-model="form.assignee_id"
            placeholder="请选择要分配的用户"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="user in availableUsers"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="分配说明" prop="notes">
          <el-input
            v-model="form.notes"
            type="textarea"
            :rows="3"
            placeholder="请输入分配说明（可选）"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button 
            type="primary" 
            @click="submitAssignment"
            :loading="loading"
          >
            {{ editingAssignment ? '更新分配' : '分配任务' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 任务分配列表 -->
    <div v-if="assignments.length > 0" class="assignments-list">
      <h4>任务分配情况</h4>
      <el-table :data="assignments" style="width: 100%">
        <el-table-column prop="assignee.username" label="被分配者" />
        <el-table-column prop="assigner.username" label="分配者" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="assigned_at" label="分配时间">
          <template #default="{ row }">
            {{ formatDate(row.assigned_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button 
              v-if="canManageAssignment(row)"
              size="small" 
              type="primary"
              @click="editAssignment(row)"
            >
              编辑
            </el-button>
            <el-button 
              v-if="row.assignee_id === currentUser.id && row.status === 'assigned'"
              size="small" 
              type="success"
              @click="acceptAssignment(row.id)"
            >
              接受
            </el-button>
            <el-button 
              v-if="row.assignee_id === currentUser.id && row.status === 'assigned'"
              size="small" 
              type="warning"
              @click="showRejectDialog(row.id)"
            >
              拒绝
            </el-button>
            <el-button 
              v-if="row.assignee_id === currentUser.id && row.status === 'accepted'"
              size="small" 
              type="success"
              @click="completeAssignment(row.id)"
            >
              完成
            </el-button>
            <el-button 
              v-if="canManageAssignment(row)"
              size="small" 
              type="danger"
              @click="deleteAssignment(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 拒绝原因对话框 -->
    <el-dialog
      v-model="rejectDialogVisible"
      title="拒绝任务分配"
      width="400px"
    >
      <el-input
        v-model="rejectionReason"
        type="textarea"
        :rows="3"
        placeholder="请输入拒绝原因（可选）"
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="rejectDialogVisible = false">取消</el-button>
          <el-button 
            type="danger" 
            @click="rejectAssignment"
            :loading="rejectLoading"
          >
            确认拒绝
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'

const props = defineProps({
  todoId: {
    type: Number,
    required: true
  },
  currentUser: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['assignments-updated'])

const dialogVisible = ref(false)
const rejectDialogVisible = ref(false)
const loading = ref(false)
const rejectLoading = ref(false)
const editingAssignment = ref(null)
const currentRejectId = ref(null)
const rejectionReason = ref('')

const form = ref({
  assignee_id: null,
  notes: ''
})

const rules = {
  assignee_id: [
    { required: true, message: '请选择被分配的用户', trigger: 'change' }
  ]
}

const assignments = ref([])
const availableUsers = ref([])

const formRef = ref()

// 计算属性
const canManageAssignment = computed(() => (assignment) => {
  return props.currentUser.id === assignment.assigner_id || 
         props.currentUser.id === assignment.todo.user_id
})

// 方法
const getStatusType = (status) => {
  const statusMap = {
    'assigned': 'info',
    'accepted': 'primary',
    'rejected': 'danger',
    'completed': 'success'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status) => {
  const statusMap = {
    'assigned': '已分配',
    'accepted': '已接受',
    'rejected': '已拒绝',
    'completed': '已完成'
  }
  return statusMap[status] || status
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN')
}

const loadAssignments = async () => {
  try {
    const response = await api.get(`/assignments/todo/${props.todoId}`)
    assignments.value = response.data
    emit('assignments-updated', assignments.value)
  } catch (error) {
    console.error('加载任务分配失败:', error)
  }
}

const loadAvailableUsers = async () => {
  try {
    // 这里应该调用获取共享清单成员的API
    // 暂时使用模拟数据
    const response = await api.get('/users')
    availableUsers.value = response.data.filter(user => user.id !== props.currentUser.id)
  } catch (error) {
    console.error('加载用户列表失败:', error)
    // 使用模拟数据
    availableUsers.value = [
      { id: 2, username: '张三' },
      { id: 3, username: '李四' },
      { id: 4, username: '王五' }
    ].filter(user => user.id !== props.currentUser.id)
  }
}

const openAssignmentDialog = () => {
  editingAssignment.value = null
  form.value = { assignee_id: null, notes: '' }
  dialogVisible.value = true
}

const editAssignment = (assignment) => {
  editingAssignment.value = assignment
  form.value = {
    assignee_id: assignment.assignee_id,
    notes: assignment.notes || ''
  }
  dialogVisible.value = true
}

const submitAssignment = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      if (editingAssignment.value) {
        // 更新分配
        await api.put(`/assignments/${editingAssignment.value.id}`, {
          assignee_id: form.value.assignee_id,
          notes: form.value.notes
        })
        ElMessage.success('任务分配更新成功')
      } else {
        // 创建新分配
        await api.post('/assignments', {
          todo_id: props.todoId,
          assignee_id: form.value.assignee_id,
          notes: form.value.notes
        })
        ElMessage.success('任务分配成功')
      }
      
      dialogVisible.value = false
      await loadAssignments()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      loading.value = false
    }
  })
}

const acceptAssignment = async (assignmentId) => {
  try {
    await api.post(`/assignments/${assignmentId}/accept`)
    ElMessage.success('已接受任务分配')
    await loadAssignments()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '接受失败')
  }
}

const showRejectDialog = (assignmentId) => {
  currentRejectId.value = assignmentId
  rejectionReason.value = ''
  rejectDialogVisible.value = true
}

const rejectAssignment = async () => {
  if (!currentRejectId.value) return
  
  rejectLoading.value = true
  try {
    await api.post(`/assignments/${currentRejectId.value}/reject`, {
      rejection_reason: rejectionReason.value
    })
    ElMessage.success('已拒绝任务分配')
    rejectDialogVisible.value = false
    await loadAssignments()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '拒绝失败')
  } finally {
    rejectLoading.value = false
  }
}

const completeAssignment = async (assignmentId) => {
  try {
    await ElMessageBox.confirm('确认完成此任务分配吗？', '确认完成', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.post(`/assignments/${assignmentId}/complete`)
    ElMessage.success('任务分配已完成')
    await loadAssignments()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '完成失败')
    }
  }
}

const deleteAssignment = async (assignmentId) => {
  try {
    await ElMessageBox.confirm('确认删除此任务分配吗？', '确认删除', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.delete(`/assignments/${assignmentId}`)
    ElMessage.success('任务分配已删除')
    await loadAssignments()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  editingAssignment.value = null
}

// 暴露方法给父组件
defineExpose({
  openAssignmentDialog,
  loadAssignments
})

// 生命周期
onMounted(() => {
  loadAssignments()
  loadAvailableUsers()
})
</script>

<style scoped>
.task-assignment {
  margin-top: 20px;
}

.assignments-list {
  margin-top: 20px;
}

.assignments-list h4 {
  margin-bottom: 15px;
  color: #333;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>