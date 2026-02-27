<template>
  <div class="todo-list">
    <div class="list-header">
      <h2>我的待办事项</h2>
      <el-button type="primary" @click="showAddDialog = true">
        添加待办
      </el-button>
    </div>

    <!-- 实时同步状态 -->
    <el-card class="sync-status-card" style="margin-bottom: 20px;">
      <el-row :gutter="20" align="middle">
        <el-col :span="12">
          <div style="display: flex; align-items: center; gap: 15px;">
            <el-tag 
              :type="syncStatus.connected ? 'success' : syncStatus.connecting ? 'warning' : 'danger'" 
              effect="dark"
            >
              {{ syncStatus.connected ? '已连接' : syncStatus.connecting ? '连接中...' : '未连接' }}
            </el-tag>
            <span>在线用户: {{ syncStatus.onlineUsers }}</span>
            <span>待办事项: {{ syncStatus.todoCount }}</span>
          </div>
        </el-col>
        <el-col :span="12" style="text-align: right;">
          <el-button 
            v-if="!syncStatus.connected" 
            type="primary" 
            size="small" 
            @click="reconnectSync"
            :loading="syncStatus.connecting"
          >
            重新连接
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 统计信息 -->
    <el-card class="stats-card">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-number">{{ todosStore.stats.total }}</div>
            <div class="stat-label">总计</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-number completed">{{ todosStore.stats.completed }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-number pending">{{ todosStore.stats.pending }}</div>
            <div class="stat-label">待完成</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-number rate">{{ todosStore.stats.completion_rate }}%</div>
            <div class="stat-label">完成率</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 待办事项列表 -->
    <el-table 
      :data="todosStore.todos" 
      style="width: 100%" 
      v-loading="todosStore.loading"
    >
      <el-table-column prop="title" label="标题" width="200" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="category" label="分类" width="120" />
      <el-table-column prop="priority" label="优先级" width="100">
        <template #default="scope">
          <el-tag 
            :type="getPriorityType(scope.row.priority)"
            effect="dark"
          >
            {{ scope.row.priority }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="due_date" label="截止日期" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.due_date) }}
        </template>
      </el-table-column>
      <el-table-column prop="completed" label="状态" width="100">
        <template #default="scope">
          <el-switch
            v-model="scope.row.completed"
            @change="toggleComplete(scope.row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="300">
        <template #default="scope">
          <el-button size="small" @click="editTodo(scope.row)">编辑</el-button>
          <el-button 
            size="small" 
            type="primary" 
            @click="openAssignment(scope.row)"
          >
            分配
          </el-button>
          <el-button 
            size="small" 
            type="success" 
            @click="openProgress(scope.row)"
          >
            进度
          </el-button>
          <el-button 
            size="small" 
            type="warning" 
            @click="openSubtasks(scope.row)"
          >
            子任务
          </el-button>
          <el-button 
            size="small" 
            type="danger" 
            @click="deleteTodo(scope.row.id)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingTodo ? '编辑待办事项' : '添加待办事项'"
      width="500px"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input type="textarea" v-model="form.description" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-input v-model="form.category" />
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
            placeholder="选择日期时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确定</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 任务分配对话框 -->
    <el-dialog
      v-model="showAssignmentDialog"
      title="任务分配"
      width="800px"
      destroy-on-close
    >
      <task-assignment
        v-if="currentTodo"
        :todo-id="currentTodo.id"
        :current-user="currentUser"
        ref="assignmentComponent"
        @assignments-updated="onAssignmentsUpdated"
      />
    </el-dialog>
    
    <!-- 进度跟踪对话框 -->
    <el-dialog
      v-model="showProgressDialog"
      title="进度跟踪"
      width="800px"
      destroy-on-close
    >
      <progress-tracking
        v-if="currentTodo"
        :todo-id="currentTodo.id"
        :current-user="currentUser"
        :can-update-progress="true"
        ref="progressComponent"
        @progress-updated="onProgressUpdated"
      />
    </el-dialog>
    
    <!-- 子任务管理对话框 -->
    <el-dialog
      v-model="showSubtasksDialog"
      :title="`子任务管理 - ${currentTodo?.title || ''}`"
      width="800px"
      destroy-on-close
    >
      <subtask-manager
        v-if="currentTodo"
        :parent-todo-id="currentTodo.id"
        ref="subtaskComponent"
        @subtasks-updated="onSubtasksUpdated"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, onUnmounted } from 'vue'
import { useTodosStore } from '../stores/todos'
import { useAuthStore } from '../stores/auth'
import { useTodoSync } from '../composables/useRealtimeSync'
import { ElMessage, ElMessageBox } from 'element-plus'
import TaskAssignment from './TaskAssignment.vue'
import ProgressTracking from './ProgressTracking.vue'
import SubtaskManager from './SubtaskManager.vue'

const todosStore = useTodosStore()
const authStore = useAuthStore()
const {
  isConnected,
  isConnecting,
  onlineUsers,
  sendTodoUpdate,
  sendTodoCreate,
  sendTodoDelete
} = useTodoSync()

const showAddDialog = ref(false)
const showAssignmentDialog = ref(false)
const showProgressDialog = ref(false)
const showSubtasksDialog = ref(false)
const editingTodo = ref(null)
const currentTodo = ref(null)
const formRef = ref()
const assignmentComponent = ref()
const progressComponent = ref()
const subtaskComponent = ref()

const currentUser = computed(() => authStore.user)

// 实时同步状态显示
const syncStatus = computed(() => ({
  connected: isConnected.value,
  connecting: isConnecting.value,
  onlineUsers: onlineUsers.value,
  todoCount: todosStore.todos.length
}))

const form = reactive({
  title: '',
  description: '',
  category: '默认',
  priority: 'medium',
  due_date: null
})

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }]
}

onMounted(() => {
  todosStore.fetchTodos()
  
  // 监听实时同步事件
  window.addEventListener('realtime-sync-update', handleRealtimeUpdate)
})

onUnmounted(() => {
  // 移除事件监听
  window.removeEventListener('realtime-sync-update', handleRealtimeUpdate)
})

const getPriorityType = (priority) => {
  const types = {
    low: 'success',
    medium: 'warning',
    high: 'danger'
  }
  return types[priority] || 'info'
}

const formatDate = (dateString) => {
  if (!dateString) return '无'
  return new Date(dateString).toLocaleString('zh-CN')
}

const toggleComplete = async (todo) => {
  const result = await todosStore.updateTodo(todo.id, { completed: todo.completed })
  if (result.success) {
    ElMessage.success('更新成功')
    // 发送实时同步
    await sendRealtimeUpdate('update', todo)
  } else {
    ElMessage.error(result.message)
    // 如果更新失败，恢复原来的状态
    todo.completed = !todo.completed
  }
}

const editTodo = (todo) => {
  editingTodo.value = todo
  Object.assign(form, {
    title: todo.title,
    description: todo.description,
    category: todo.category,
    priority: todo.priority,
    due_date: todo.due_date
  })
  showAddDialog.value = true
}

const deleteTodo = async (id) => {
  await ElMessageBox.confirm('确定要删除这个待办事项吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
  
  const result = await todosStore.deleteTodo(id)
  if (result.success) {
    ElMessage.success('删除成功')
    // 发送实时同步
    await sendRealtimeUpdate('delete', { id })
  } else {
    ElMessage.error(result.message)
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      let result
      let todoData
      if (editingTodo.value) {
        result = await todosStore.updateTodo(editingTodo.value.id, form)
        todoData = { ...editingTodo.value, ...form }
      } else {
        result = await todosStore.addTodo(form)
        todoData = result.data
      }
      
      if (result.success) {
        ElMessage.success(editingTodo.value ? '更新成功' : '添加成功')
        showAddDialog.value = false
        resetForm()
        
        // 发送实时同步
        if (todoData) {
          await sendRealtimeUpdate(
            editingTodo.value ? 'update' : 'create', 
            todoData
          )
        }
      } else {
        ElMessage.error(result.message)
      }
    }
  })
}

const resetForm = () => {
  editingTodo.value = null
  Object.assign(form, {
    title: '',
    description: '',
    category: '默认',
    priority: 'medium',
    due_date: null
  })
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

const openAssignment = (todo) => {
  currentTodo.value = todo
  showAssignmentDialog.value = true
  // 延迟加载分配数据
  setTimeout(() => {
    if (assignmentComponent.value) {
      assignmentComponent.value.loadAssignments()
    }
  }, 100)
}

const openProgress = (todo) => {
  currentTodo.value = todo
  showProgressDialog.value = true
  // 延迟加载进度数据
  setTimeout(() => {
    if (progressComponent.value) {
      progressComponent.value.loadProgressTracks()
      progressComponent.value.loadProgressStats()
    }
  }, 100)
}

const openSubtasks = (todo) => {
  currentTodo.value = todo
  showSubtasksDialog.value = true
  // 延迟加载子任务数据
  setTimeout(() => {
    if (subtaskComponent.value) {
      subtaskComponent.value.loadSubtasks()
    }
  }, 100)
}

const onAssignmentsUpdated = (assignments) => {
  console.log('任务分配已更新:', assignments)
  // 可以在这里更新相关的统计数据
}

const onProgressUpdated = (progressTracks) => {
  console.log('进度已更新:', progressTracks)
  // 可以在这里更新相关的统计数据
}

const onSubtasksUpdated = (subtasks) => {
  console.log('子任务已更新:', subtasks)
  // 刷新主任务列表以更新统计信息
  todosStore.fetchTodos()
  // 可以在这里更新相关的统计数据
}

// 实时同步相关方法
const reconnectSync = () => {
  // 重新初始化同步连接
  window.location.reload()
}

// 监听实时同步更新
const handleRealtimeUpdate = (event) => {
  const message = event.detail
  console.log('收到实时更新:', message)
  
  // 根据消息类型处理更新
  switch (message.data?.action) {
    case 'todo_create':
      // 有新的待办事项创建
      todosStore.fetchTodos()
      ElMessage.info(`${message.sender_id} 创建了新的待办事项`)
      break
    case 'todo_update':
      // 待办事项被更新
      todosStore.fetchTodos()
      ElMessage.info(`${message.sender_id} 更新了待办事项`)
      break
    case 'todo_delete':
      // 待办事项被删除
      todosStore.fetchTodos()
      ElMessage.info(`${message.sender_id} 删除了待办事项`)
      break
  }
}

// 发送实时同步消息
const sendRealtimeUpdate = async (action, todoData) => {
  if (isConnected.value) {
    switch (action) {
      case 'create':
        await sendTodoCreate(todoData)
        break
      case 'update':
        await sendTodoUpdate(todoData)
        break
      case 'delete':
        await sendTodoDelete(todoData.id)
        break
    }
  }
}
</script>

<style scoped>
.todo-list {
  padding: 20px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.stats-card {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.stat-number.completed {
  color: #67c23a;
}

.stat-number.pending {
  color: #e6a23c;
}

.stat-number.rate {
  color: #909399;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  margin-top: 5px;
}
</style>