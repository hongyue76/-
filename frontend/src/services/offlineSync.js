import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'

// 离线操作类型枚举
export const OperationType = {
  CREATE: 'CREATE',
  UPDATE: 'UPDATE', 
  DELETE: 'DELETE'
}

// 离线操作类
export class OfflineOperation {
  constructor(todoId, operationType, fieldName = null, oldValue = null, newValue = null) {
    this.id = Date.now() + Math.random() // 临时ID
    this.todoId = todoId
    this.operationType = operationType
    this.fieldName = fieldName
    this.oldValue = oldValue
    this.newValue = newValue
    this.timestamp = new Date()
    this.sequenceId = this.generateSequenceId()
    this.deviceId = this.getDeviceId()
    this.syncStatus = 'pending'
  }

  generateSequenceId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  getDeviceId() {
    // 简单的设备标识生成
    return localStorage.getItem('device_id') || this.generateDeviceId()
  }

  generateDeviceId() {
    const deviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem('device_id', deviceId)
    return deviceId
  }

  toJSON() {
    return {
      todo_id: this.todoId,
      operation_type: this.operationType,
      field_name: this.fieldName,
      old_value: this.oldValue,
      new_value: this.newValue,
      device_id: this.deviceId
    }
  }
}

// 离线同步服务
export class OfflineSyncService {
  constructor() {
    this.operations = ref([])
    this.isOnline = ref(navigator.onLine)
    this.syncInterval = null
    this.authStore = null
    this.BASE_URL = 'http://localhost:8000/api'
    
    this.initialize()
  }

  /**
   * 延迟初始化store，确保在Pinia激活后调用
   */
  initStore() {
    if (!this.authStore) {
      this.authStore = useAuthStore()
    }
    return this.authStore
  }

  initialize() {
    // 加载本地存储的操作
    this.loadFromStorage()
    
    // 监听网络状态变化
    window.addEventListener('online', () => {
      this.isOnline.value = true
      this.triggerSync()
    })
    
    window.addEventListener('offline', () => {
      this.isOnline.value = false
    })
    
    // 定期同步
    this.startAutoSync()
  }

  // 记录操作
  recordOperation(operation) {
    this.operations.value.push(operation)
    this.saveToStorage()
    
    // 如果在线，立即尝试同步
    if (this.isOnline.value) {
      this.scheduleSync()
    }
  }

  // 更新操作（幂等性保证）
  updateOperation(todoId, field, newValue, oldValue = null) {
    const operation = new OfflineOperation(
      todoId,
      OperationType.UPDATE,
      field,
      oldValue,
      newValue
    )
    
    this.recordOperation(operation)
    return operation
  }

  // 删除操作
  deleteOperation(todoId) {
    const operation = new OfflineOperation(
      todoId,
      OperationType.DELETE
    )
    
    this.recordOperation(operation)
    return operation
  }

  // 创建操作
  createOperation(todoData) {
    const operation = new OfflineOperation(
      null, // 新创建的任务暂时没有ID
      OperationType.CREATE,
      null,
      null,
      JSON.stringify(todoData)
    )
    
    this.recordOperation(operation)
    return operation
  }

  // 合并相同字段的操作
  mergePendingOperations() {
    const merged = []
    const operationGroups = new Map()
    
    // 按todoId和fieldName分组
    this.operations.value.forEach(op => {
      if (op.syncStatus === 'pending') {
        const key = `${op.todoId}-${op.fieldName}`
        if (!operationGroups.has(key)) {
          operationGroups.set(key, [])
        }
        operationGroups.get(key).push(op)
      }
    })
    
    // 对每组只保留最新的操作
    operationGroups.forEach((ops, key) => {
      if (ops.length > 0) {
        // 按时间戳排序，保留最新的
        const latestOp = ops.reduce((latest, current) => 
          current.timestamp > latest.timestamp ? current : latest
        )
        merged.push(latestOp)
      }
    })
    
    return merged
  }

  // 触发同步
  async triggerSync() {
    const authStore = this.initStore()
    if (!authStore.isAuthenticated) {
      console.log('用户未认证，跳过同步')
      return
    }
    
    try {
      const mergedOperations = this.mergePendingOperations()
      
      if (mergedOperations.length === 0) {
        console.log('没有待同步的操作')
        return
      }
      
      console.log(`开始同步 ${mergedOperations.length} 个操作`)
      
      const response = await axios.post(`${this.BASE_URL}/offline/sync`, {
        last_sync_time: this.getLastSyncTime(),
        device_id: this.getDeviceId(),
        pending_operations: mergedOperations.map(op => op.toJSON())
      }, {
        headers: {
          'Authorization': `Bearer ${this.initStore().token}`,
          'Content-Type': 'application/json'
        }
      })
      
      // 处理服务器响应
      await this.handleSyncResponse(response.data)
      
    } catch (error) {
      console.error('同步失败:', error)
      // 网络错误时保持操作在队列中
    }
  }

  // 处理同步响应
  async handleSyncResponse(syncData) {
    console.log('同步响应:', syncData)
    
    // 更新本地数据
    if (syncData.server_updates && syncData.server_updates.length > 0) {
      this.updateLocalData(syncData.server_updates)
    }
    
    // 处理冲突
    if (syncData.conflicts && syncData.conflicts.length > 0) {
      await this.handleConflicts(syncData.conflicts)
    }
    
    // 标记已同步的操作
    this.markOperationsAsSynced(syncData.sync_timestamp)
    
    // 清理已同步的操作
    this.cleanupSyncedOperations()
    
    // 更新最后同步时间
    this.updateLastSyncTime(syncData.sync_timestamp)
  }

  // 处理冲突
  async handleConflicts(conflicts) {
    console.log('发现冲突:', conflicts)
    
    for (const conflict of conflicts) {
      // 显示冲突详情给用户
      const userChoice = await this.promptUserForConflictResolution(conflict)
      
      // 根据用户选择解决冲突
      await this.resolveConflict(
        conflict.operation_id, 
        userChoice.resolution,
        userChoice.mergedData
      )
    }
  }
  
  // 提示用户解决冲突
  async promptUserForConflictResolution(conflict) {
    // 在实际应用中，这里应该显示一个友好的UI对话框
    console.log('=== 冲突详情 ===')
    console.log(`任务ID: ${conflict.todo_id}`)
    console.log(`字段: ${conflict.field}`)
    console.log(`服务器当前值: ${conflict.server_value}`)
    console.log(`您的原始值: ${conflict.client_old_value}`)
    console.log(`您的新值: ${conflict.client_new_value}`)
    
    // 根据字段类型提供智能建议
    const strategy = this.getConflictResolutionStrategy()
    
    switch(strategy) {
      case 'server_wins':
        console.log('采用策略: 保留服务器版本')
        return { resolution: 'accept_server' }
      
      case 'client_wins':
        console.log('采用策略: 保留您的版本')
        return { resolution: 'accept_client' }
      
      case 'smart_merge':
        // 智能合并
        const mergedValue = this.smartMergeValues(
          conflict.server_value, 
          conflict.client_new_value, 
          conflict.field
        )
        console.log(`采用策略: 智能合并 -> ${mergedValue}`)
        return { 
          resolution: 'merge',
          mergedData: { [conflict.field]: mergedValue }
        }
      
      case 'prompt_user':
      default:
        // 实际应用中应该显示真正的UI对话框
        console.log('提示用户选择解决方案...')
        // 模拟用户选择了智能合并
        const userMergedValue = this.smartMergeValues(
          conflict.server_value, 
          conflict.client_new_value, 
          conflict.field
        )
        return { 
          resolution: 'merge',
          mergedData: { [conflict.field]: userMergedValue }
        }
    }
  }
  
  // 获取冲突解决策略（可以配置）
  getConflictResolutionStrategy() {
    // 可以根据应用配置或用户偏好来决定
    // 例如：'server_wins' | 'client_wins' | 'smart_merge' | 'prompt_user'
    const config = localStorage.getItem('conflict_resolution_strategy')
    return config || 'smart_merge' // 默认采用智能合并策略
  }
  
  // 智能合并不同类型的数据
  smartMergeValues(serverValue, clientValue, fieldType) {
    switch(fieldType) {
      case 'title':
      case 'description':
        // 文本字段：智能合并
        if (serverValue && clientValue) {
          return `${serverValue} & ${clientValue}`
        }
        return serverValue || clientValue
      
      case 'priority':
        // 优先级：取较高优先级
        const priorityOrder = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        return priorityOrder[serverValue] >= priorityOrder[clientValue] ? serverValue : clientValue
      
      case 'completed':
        // 布尔值：OR运算（有一个完成就算完成）
        return serverValue || clientValue
      
      case 'due_date':
        // 日期：取较早的截止日期
        if (serverValue && clientValue) {
          return new Date(serverValue) <= new Date(clientValue) ? serverValue : clientValue
        }
        return serverValue || clientValue
      
      default:
        // 默认：保留服务端值
        return serverValue
    }
  }

  // 解决冲突
  async resolveConflict(operationId, resolution, mergedData = null) {
    try {
      await axios.post(`${this.BASE_URL}/offline/resolve-conflict`, {
        operation_id: operationId,
        resolution: resolution,
        merged_data: mergedData
      }, {
        headers: {
          'Authorization': `Bearer ${this.initStore().token}`,
          'Content-Type': 'application/json'
        }
      })
    } catch (error) {
      console.error('冲突解决失败:', error)
    }
  }

  // 更新本地数据
  updateLocalData(updates) {
    // 这里应该通知相关的store更新数据
    // 具体实现取决于你的状态管理方案
    window.dispatchEvent(new CustomEvent('offline-data-updated', {
      detail: { updates }
    }))
  }

  // 标记操作为已同步
  markOperationsAsSynced(syncTimestamp) {
    this.operations.value.forEach(op => {
      if (op.syncStatus === 'pending' && op.timestamp <= new Date(syncTimestamp)) {
        op.syncStatus = 'synced'
      }
    })
    this.saveToStorage()
  }

  // 清理已同步的操作
  cleanupSyncedOperations() {
    // 保留最近的操作记录，清理很久以前的已同步操作
    const cutoffTime = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) // 一周前
    
    this.operations.value = this.operations.value.filter(op => {
      return op.syncStatus !== 'synced' || op.timestamp > cutoffTime
    })
    
    this.saveToStorage()
  }

  // 调度同步
  scheduleSync(delay = 1000) {
    clearTimeout(this.syncTimeout)
    this.syncTimeout = setTimeout(() => {
      this.triggerSync()
    }, delay)
  }

  // 自动同步
  startAutoSync() {
    this.syncInterval = setInterval(() => {
      if (this.isOnline.value && this.operations.value.some(op => op.syncStatus === 'pending')) {
        this.triggerSync()
      }
    }, 30000) // 每30秒检查一次
  }

  // 存储操作到本地
  saveToStorage() {
    try {
      localStorage.setItem('offline_operations', JSON.stringify(this.operations.value))
    } catch (error) {
      console.error('保存离线操作失败:', error)
    }
  }

  // 从本地存储加载操作
  loadFromStorage() {
    try {
      const stored = localStorage.getItem('offline_operations')
      if (stored) {
        this.operations.value = JSON.parse(stored).map(opData => {
          const op = new OfflineOperation()
          Object.assign(op, opData)
          op.timestamp = new Date(op.timestamp)
          return op
        })
      }
    } catch (error) {
      console.error('加载离线操作失败:', error)
      this.operations.value = []
    }
  }

  // 获取最后同步时间
  getLastSyncTime() {
    const lastSync = localStorage.getItem('last_sync_time')
    return lastSync ? new Date(lastSync) : null
  }

  // 更新最后同步时间
  updateLastSyncTime(timestamp) {
    localStorage.setItem('last_sync_time', timestamp.toISOString())
  }

  // 获取设备ID
  getDeviceId() {
    return localStorage.getItem('device_id') || this.generateDeviceId()
  }

  // 生成设备ID
  generateDeviceId() {
    const deviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem('device_id', deviceId)
    return deviceId
  }

  // 销毁服务
  destroy() {
    clearInterval(this.syncInterval)
    clearTimeout(this.syncTimeout)
    window.removeEventListener('online', this.triggerSync)
    window.removeEventListener('offline', () => {})
  }
}

// 创建全局实例
export const offlineSyncService = new OfflineSyncService()

// Composable hook
export function useOfflineSync() {
  return {
    operations: offlineSyncService.operations,
    isOnline: offlineSyncService.isOnline,
    recordOperation: offlineSyncService.recordOperation.bind(offlineSyncService),
    updateOperation: offlineSyncService.updateOperation.bind(offlineSyncService),
    deleteOperation: offlineSyncService.deleteOperation.bind(offlineSyncService),
    createOperation: offlineSyncService.createOperation.bind(offlineSyncService),
    triggerSync: offlineSyncService.triggerSync.bind(offlineSyncService)
  }
}