import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../utils/api'
import { localStorageService } from '../utils/localStorageService'
import { useNetwork } from '../utils/networkMonitor'
import { useOfflineSync, OperationType } from '../services/offlineSync'

export const useTodosStore = defineStore('todos', () => {
  const todos = ref([])
  const loading = ref(false)
  const stats = ref({ total: 0, completed: 0, pending: 0, completion_rate: 0 })
  const { isOnline } = useNetwork()
  const { updateOperation, createOperation, deleteOperation } = useOfflineSync()

  const fetchTodos = async () => {
    loading.value = true
    try {
      if (isOnline.value) {
        // 在线模式：从服务器获取数据
        const response = await api.get('/todos/')
        todos.value = response.data
        
        // 同时更新本地存储
        for (const todo of response.data) {
          await localStorageService.addItem('todos', {
            ...todo,
            sync_status: 'synced'
          })
        }
      } else {
        // 离线模式：从本地存储获取数据
        const localTodos = await localStorageService.getAllItems('todos')
        todos.value = localTodos
      }
      
      await fetchStats()
    } catch (error) {
      console.error('获取待办事项失败:', error)
      // 出错时尝试从本地存储获取
      try {
        const localTodos = await localStorageService.getAllItems('todos')
        todos.value = localTodos
      } catch (localError) {
        console.error('本地数据获取也失败:', localError)
      }
    } finally {
      loading.value = false
    }
  }

  const addTodo = async (todoData) => {
    try {
      if (isOnline.value) {
        // 在线模式：直接发送到服务器
        const response = await api.post('/todos/', todoData)
        todos.value.push(response.data)
        
        // 更新本地存储
        await localStorageService.addItem('todos', {
          ...response.data,
          sync_status: 'synced'
        })
        
        await fetchStats()
        return { success: true, data: response.data }
      } else {
        // 离线模式：使用离线同步服务
        const operation = createOperation(todoData)
        
        const localTodo = {
          ...todoData,
          id: operation.id, // 使用操作ID作为临时ID
          user_id: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          sync_status: 'pending',
          operation_id: operation.id
        }
        
        todos.value.push(localTodo)
        await localStorageService.addItem('todos', localTodo)
        await fetchStats()
        
        return { 
          success: true, 
          data: localTodo,
          message: '已保存到本地，网络恢复后自动同步'
        }
      }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '添加失败' 
      }
    }
  }

  const updateTodo = async (id, todoData) => {
    try {
      const todoIndex = todos.value.findIndex(todo => todo.id === id)
      if (todoIndex === -1) {
        return { success: false, message: '待办事项不存在' }
      }

      const originalTodo = todos.value[todoIndex]

      if (isOnline.value) {
        // 在线模式：更新服务器数据
        const response = await api.put(`/todos/${id}`, todoData)
        
        // 更新内存和本地存储
        todos.value[todoIndex] = response.data
        await localStorageService.updateItem('todos', {
          ...response.data,
          sync_status: 'synced'
        })
        
        await fetchStats()
        return { success: true, data: response.data }
      } else {
        // 离线模式：使用离线同步服务记录变更
        Object.keys(todoData).forEach(field => {
          if (todoData[field] !== originalTodo[field]) {
            updateOperation(id, field, todoData[field], originalTodo[field])
          }
        })
        
        const updatedTodo = {
          ...originalTodo,
          ...todoData,
          updated_at: new Date().toISOString(),
          sync_status: 'modified'
        }
        
        todos.value[todoIndex] = updatedTodo
        await localStorageService.updateItem('todos', updatedTodo)
        await fetchStats()
        
        return { 
          success: true, 
          data: updatedTodo,
          message: '已保存到本地，网络恢复后自动同步'
        }
      }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '更新失败' 
      }
    }
  }

  const deleteTodo = async (id) => {
    try {
      const todoIndex = todos.value.findIndex(todo => todo.id === id)
      if (todoIndex === -1) {
        return { success: false, message: '待办事项不存在' }
      }

      const todoToDelete = todos.value[todoIndex]

      if (isOnline.value) {
        // 在线模式：删除服务器数据
        await api.delete(`/todos/${id}`)
        
        // 更新内存和本地存储
        todos.value.splice(todoIndex, 1)
        await localStorageService.deleteItem('todos', id)
        
        await fetchStats()
        return { success: true }
      } else {
        // 离线模式：使用离线同步服务
        deleteOperation(id)
        
        const deletedTodo = {
          ...todoToDelete,
          deleted_at: new Date().toISOString(),
          sync_status: 'deleted'
        }
        
        todos.value.splice(todoIndex, 1)
        await localStorageService.deleteItem('todos', id, deletedTodo)
        await fetchStats()
        
        return { 
          success: true, 
          message: '已标记删除，网络恢复后自动同步'
        }
      }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '删除失败' 
      }
    }
  }

  const fetchStats = async () => {
    try {
      if (isOnline.value) {
        const response = await api.get('/todos/stats/completion')
        stats.value = response.data
      } else {
        // 离线模式：基于本地数据计算统计
        const completed = todos.value.filter(todo => todo.completed).length
        const total = todos.value.length
        stats.value = {
          total,
          completed,
          pending: total - completed,
          completion_rate: total > 0 ? Math.round((completed / total) * 100) : 0
        }
      }
    } catch (error) {
      console.error('获取统计信息失败:', error)
    }
  }

  const getTodosByCategory = (category) => {
    return todos.value.filter(todo => todo.category === category)
  }

  const getCompletedTodos = () => {
    return todos.value.filter(todo => todo.completed)
  }

  const getPendingTodos = () => {
    return todos.value.filter(todo => !todo.completed)
  }

  // 同步本地待办事项到服务器
  const syncLocalTodos = async () => {
    if (!isOnline.value) return { success: false, message: '网络不可用' }
    
    try {
      const localTodos = await localStorageService.getAllItems('todos')
      const unsyncedTodos = localTodos.filter(todo => 
        todo.sync_status === 'pending' || todo.sync_status === 'modified'
      )
      
      let syncedCount = 0
      for (const todo of unsyncedTodos) {
        try {
          if (todo.sync_status === 'pending') {
            // 创建新待办事项
            const response = await api.post('/todos/', {
              title: todo.title,
              description: todo.description,
              priority: todo.priority,
              category: todo.category,
              due_date: todo.due_date
            })
            
            // 更新本地ID映射
            await localStorageService.updateItem('todos', {
              ...todo,
              id: response.data.id,
              sync_status: 'synced'
            })
          } else if (todo.sync_status === 'modified') {
            // 更新现有待办事项
            await api.put(`/todos/${todo.id}`, {
              title: todo.title,
              description: todo.description,
              priority: todo.priority,
              category: todo.category,
              due_date: todo.due_date,
              completed: todo.completed
            })
            
            await localStorageService.updateItem('todos', {
              ...todo,
              sync_status: 'synced'
            })
          }
          syncedCount++
        } catch (error) {
          console.error(`同步待办事项 ${todo.id} 失败:`, error)
        }
      }
      
      // 刷新数据
      await fetchTodos()
      
      return { 
        success: true, 
        message: `成功同步 ${syncedCount} 个待办事项`,
        count: syncedCount
      }
    } catch (error) {
      return { success: false, message: '同步失败: ' + error.message }
    }
  }

  return {
    todos,
    loading,
    stats,
    fetchTodos,
    addTodo,
    updateTodo,
    deleteTodo,
    fetchStats,
    getTodosByCategory,
    getCompletedTodos,
    getPendingTodos,
    syncLocalTodos
  }
})