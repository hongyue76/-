import { ref, reactive, onMounted, onUnmounted } from 'vue'
import websocketClient from '../utils/websocketClient'
import { useAuthStore } from '../stores/auth'

/**
 * 实时同步组合式API
 * @param {Array} initialRooms - 初始房间列表
 */
export function useRealtimeSync(initialRooms = []) {
  // 响应式状态
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const onlineUsers = ref(0)
  const currentRooms = reactive(new Set())
  const syncMessages = reactive([])
  const error = ref(null)

  // 认证状态
  const authStore = useAuthStore()

  /**
   * 初始化WebSocket连接
   */
  const initializeConnection = async () => {
    if (!authStore.isAuthenticated) {
      console.log('用户未登录，跳过WebSocket连接')
      return
    }

    try {
      // 连接WebSocket
      await websocketClient.connect(initialRooms)
      
      // 初始化房间
      initialRooms.forEach(room => currentRooms.add(room))
      
    } catch (err) {
      console.error('初始化WebSocket连接失败:', err)
      error.value = err.message
    }
  }

  /**
   * 处理连接确认
   */
  const handleConnectionConfirmed = (message) => {
    isConnected.value = true
    isConnecting.value = false
    onlineUsers.value = message.online_users || 0
    
    // 更新房间状态
    message.rooms?.forEach(room => currentRooms.add(room))
    
    console.log('WebSocket连接已确认:', message)
  }

  /**
   * 处理同步更新
   */
  const handleSyncUpdate = (message) => {
    // 添加到消息列表
    syncMessages.unshift({
      id: Date.now(),
      type: 'sync_update',
      sender_id: message.sender_id,
      data: message.data,
      timestamp: message.timestamp
    })
    
    // 保持消息列表长度
    if (syncMessages.length > 100) {
      syncMessages.pop()
    }
    
    console.log('收到同步更新:', message)
    
    // 触发自定义事件
    window.dispatchEvent(new CustomEvent('realtime-sync-update', {
      detail: message
    }))
  }

  /**
   * 处理房间加入确认
   */
  const handleRoomJoined = (message) => {
    if (message.success) {
      currentRooms.add(message.room_id)
      console.log(`成功加入房间: ${message.room_id}`)
    } else {
      console.error(`加入房间失败: ${message.room_id}`)
    }
  }

  /**
   * 处理房间离开确认
   */
  const handleRoomLeft = (message) => {
    if (message.success) {
      currentRooms.delete(message.room_id)
      console.log(`成功离开房间: ${message.room_id}`)
    } else {
      console.error(`离开房间失败: ${message.room_id}`)
    }
  }

  /**
   * 处理用户离开房间
   */
  const handleUserLeftRoom = (message) => {
    console.log(`用户 ${message.user_id} 离开了房间 ${message.room_id}`)
    // 可以在这里更新用户列表
  }

  /**
   * 处理错误
   */
  const handleError = (errorData) => {
    error.value = errorData.error
    console.error('WebSocket错误:', errorData)
  }

  /**
   * 发送同步数据
   * @param {string} roomId - 房间ID
   * @param {Object} data - 同步数据
   */
  const sendSyncData = (roomId, data) => {
    if (!isConnected.value) {
      console.warn('WebSocket未连接，无法发送同步数据')
      return false
    }
    
    return websocketClient.sendSyncRequest(roomId, data)
  }

  /**
   * 加入房间
   * @param {string} roomId - 房间ID
   */
  const joinRoom = async (roomId) => {
    try {
      await websocketClient.joinRoom(roomId)
      return true
    } catch (err) {
      console.error('加入房间失败:', err)
      error.value = err.message
      return false
    }
  }

  /**
   * 离开房间
   * @param {string} roomId - 房间ID
   */
  const leaveRoom = async (roomId) => {
    try {
      await websocketClient.leaveRoom(roomId)
      return true
    } catch (err) {
      console.error('离开房间失败:', err)
      error.value = err.message
      return false
    }
  }

  /**
   * 获取连接状态
   */
  const getConnectionStatus = () => {
    return {
      isConnected: isConnected.value,
      isConnecting: isConnecting.value,
      onlineUsers: onlineUsers.value,
      rooms: [...currentRooms],
      messageCount: syncMessages.length
    }
  }

  /**
   * 清理资源
   */
  const cleanup = () => {
    websocketClient.disconnect()
    syncMessages.length = 0
    currentRooms.clear()
    isConnected.value = false
    isConnecting.value = false
    error.value = null
  }

  // 设置事件监听器
  onMounted(() => {
    // 监听WebSocket客户端事件
    websocketClient.on('connection_confirmed', handleConnectionConfirmed)
    websocketClient.on('sync_update', handleSyncUpdate)
    websocketClient.on('room_joined', handleRoomJoined)
    websocketClient.on('room_left', handleRoomLeft)
    websocketClient.on('user_left_room', handleUserLeftRoom)
    websocketClient.on('error', handleError)
    
    // 监听连接状态变化
    const unwatchAuth = authStore.$subscribe((mutation, state) => {
      if (state.isAuthenticated && !isConnected.value && !isConnecting.value) {
        initializeConnection()
      } else if (!state.isAuthenticated && isConnected.value) {
        cleanup()
      }
    })
    
    // 如果已登录，立即连接
    if (authStore.isAuthenticated) {
      initializeConnection()
    }
  })

  // 清理事件监听器
  onUnmounted(() => {
    websocketClient.off('connection_confirmed', handleConnectionConfirmed)
    websocketClient.off('sync_update', handleSyncUpdate)
    websocketClient.off('room_joined', handleRoomJoined)
    websocketClient.off('room_left', handleRoomLeft)
    websocketClient.off('user_left_room', handleUserLeftRoom)
    websocketClient.off('error', handleError)
    cleanup()
  })

  return {
    // 状态
    isConnected,
    isConnecting,
    onlineUsers,
    currentRooms,
    syncMessages,
    error,
    
    // 方法
    sendSyncData,
    joinRoom,
    leaveRoom,
    getConnectionStatus,
    cleanup
  }
}

/**
 * 待办事项实时同步hook
 */
export function useTodoSync() {
  const {
    isConnected,
    isConnecting,
    onlineUsers,
    currentRooms,
    syncMessages,
    error,
    sendSyncData,
    joinRoom,
    leaveRoom,
    getConnectionStatus
  } = useRealtimeSync(['todos'])

  /**
   * 发送待办事项更新
   * @param {Object} todoData - 待办事项数据
   */
  const sendTodoUpdate = (todoData) => {
    return sendSyncData('todos', {
      action: 'todo_update',
      todo: todoData
    })
  }

  /**
   * 发送待办事项创建
   * @param {Object} todoData - 待办事项数据
   */
  const sendTodoCreate = (todoData) => {
    return sendSyncData('todos', {
      action: 'todo_create',
      todo: todoData
    })
  }

  /**
   * 发送待办事项删除
   * @param {number} todoId - 待办事项ID
   */
  const sendTodoDelete = (todoId) => {
    return sendSyncData('todos', {
      action: 'todo_delete',
      todo_id: todoId
    })
  }

  return {
    // 继承的基础状态和方法
    isConnected,
    isConnecting,
    onlineUsers,
    currentRooms,
    syncMessages,
    error,
    joinRoom,
    leaveRoom,
    getConnectionStatus,
    
    // 待办事项专用方法
    sendTodoUpdate,
    sendTodoCreate,
    sendTodoDelete
  }
}

/**
 * 任务分配实时同步hook
 */
export function useAssignmentSync() {
  const {
    isConnected,
    sendSyncData,
    joinRoom,
    leaveRoom
  } = useRealtimeSync(['assignments'])

  /**
   * 发送任务分配更新
   * @param {Object} assignmentData - 任务分配数据
   */
  const sendAssignmentUpdate = (assignmentData) => {
    return sendSyncData('assignments', {
      action: 'assignment_update',
      assignment: assignmentData
    })
  }

  /**
   * 发送任务分配创建
   * @param {Object} assignmentData - 任务分配数据
   */
  const sendAssignmentCreate = (assignmentData) => {
    return sendSyncData('assignments', {
      action: 'assignment_create',
      assignment: assignmentData
    })
  }

  return {
    isConnected,
    joinRoom,
    leaveRoom,
    sendAssignmentUpdate,
    sendAssignmentCreate
  }
}

/**
 * 进度跟踪实时同步hook
 */
export function useProgressSync() {
  const {
    isConnected,
    sendSyncData,
    joinRoom,
    leaveRoom
  } = useRealtimeSync(['progress'])

  /**
   * 发送进度更新
   * @param {Object} progressData - 进度数据
   */
  const sendProgressUpdate = (progressData) => {
    return sendSyncData('progress', {
      action: 'progress_update',
      progress: progressData
    })
  }

  return {
    isConnected,
    joinRoom,
    leaveRoom,
    sendProgressUpdate
  }
}