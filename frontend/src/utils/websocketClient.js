import { ref, reactive } from 'vue'
import { useAuthStore } from '../stores/auth'

class WebSocketClient {
  constructor() {
    this.ws = null
    this.url = ''
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.heartbeatInterval = null
    this.heartbeatTimeout = null
    this.isConnected = ref(false)
    this.isConnecting = ref(false)
    this.rooms = reactive(new Set())
    
    // 事件处理器
    this.eventHandlers = {
      'connection_confirmed': [],
      'sync_update': [],
      'room_joined': [],
      'room_left': [],
      'user_left_room': [],
      'heartbeat_ack': [],
      'error': []
    }
  }

  /**
   * 连接到WebSocket服务器
   * @param {Array} initialRooms - 初始加入的房间列表
   */
  async connect(initialRooms = []) {
    if (this.isConnecting.value || this.isConnected.value) {
      return
    }

    this.isConnecting.value = true
    const authStore = useAuthStore()
    
    if (!authStore.token) {
      throw new Error('未登录，无法建立WebSocket连接')
    }

    // 构建WebSocket URL
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws'
    const wsBaseUrl = baseUrl.replace(/^https?:\/\//, '')
    
    const roomsParam = initialRooms.length > 0 ? `&rooms=${initialRooms.join(',')}` : ''
    this.url = `${wsProtocol}://${wsBaseUrl}/api/ws/sync?token=${authStore.token}${roomsParam}`

    try {
      this.ws = new WebSocket(this.url)
      
      this.ws.onopen = () => {
        console.log('WebSocket连接已建立')
        this.isConnected.value = true
        this.isConnecting.value = false
        this.reconnectAttempts = 0
        
        // 初始化房间
        initialRooms.forEach(room => this.rooms.add(room))
        
        // 启动心跳机制
        this.startHeartbeat()
        
        // 触发连接成功事件
        this.emit('connection_confirmed', { 
          url: this.url,
          rooms: [...this.rooms]
        })
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.log('收到WebSocket消息:', message)
          
          // 处理心跳响应
          if (message.type === 'heartbeat_ack') {
            this.handleHeartbeatAck()
            return
          }
          
          // 触发对应的事件处理器
          if (this.eventHandlers[message.type]) {
            this.eventHandlers[message.type].forEach(handler => {
              handler(message)
            })
          }
          
        } catch (error) {
          console.error('解析WebSocket消息失败:', error)
          this.emit('error', { error: '消息解析失败', data: event.data })
        }
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket连接已关闭:', event.code, event.reason)
        this.cleanup()
        
        // 尝试重连
        if (event.code !== 4001 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect()
        } else {
          this.emit('error', { 
            error: '连接失败', 
            code: event.code, 
            reason: event.reason 
          })
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
        this.emit('error', { error: 'WebSocket连接错误' })
      }

    } catch (error) {
      console.error('创建WebSocket连接失败:', error)
      this.isConnecting.value = false
      this.emit('error', { error: '连接创建失败' })
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close(1000, '客户端主动断开')
    }
    this.cleanup()
  }

  /**
   * 清理连接资源
   */
  cleanup() {
    this.isConnected.value = false
    this.isConnecting.value = false
    
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
    
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout)
      this.heartbeatTimeout = null
    }
    
    this.ws = null
  }

  /**
   * 发送消息
   * @param {Object} message - 消息对象
   */
  sendMessage(message) {
    if (!this.isConnected.value || !this.ws) {
      console.warn('WebSocket未连接，消息发送失败:', message)
      return false
    }

    try {
      const messageStr = JSON.stringify(message)
      this.ws.send(messageStr)
      console.log('发送WebSocket消息:', message)
      return true
    } catch (error) {
      console.error('发送WebSocket消息失败:', error)
      this.emit('error', { error: '消息发送失败', message })
      return false
    }
  }

  /**
   * 发送同步请求
   * @param {string} roomId - 房间ID
   * @param {Object} data - 同步数据
   */
  sendSyncRequest(roomId, data) {
    return this.sendMessage({
      type: 'sync_request',
      room_id: roomId,
      data: data
    })
  }

  /**
   * 加入房间
   * @param {string} roomId - 房间ID
   */
  joinRoom(roomId) {
    if (this.rooms.has(roomId)) {
      console.log(`已在房间 ${roomId} 中`)
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const handler = (message) => {
        if (message.room_id === roomId) {
          if (message.success) {
            this.rooms.add(roomId)
            console.log(`成功加入房间: ${roomId}`)
            resolve(message)
          } else {
            console.error(`加入房间失败: ${roomId}`)
            reject(new Error('加入房间失败'))
          }
          // 移除事件监听器
          this.off('room_joined', handler)
        }
      }

      this.on('room_joined', handler)
      
      this.sendMessage({
        type: 'join_room',
        room_id: roomId
      })

      // 设置超时
      setTimeout(() => {
        this.off('room_joined', handler)
        reject(new Error('加入房间超时'))
      }, 5000)
    })
  }

  /**
   * 离开房间
   * @param {string} roomId - 房间ID
   */
  leaveRoom(roomId) {
    if (!this.rooms.has(roomId)) {
      console.log(`不在房间 ${roomId} 中`)
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const handler = (message) => {
        if (message.room_id === roomId) {
          if (message.success) {
            this.rooms.delete(roomId)
            console.log(`成功离开房间: ${roomId}`)
            resolve(message)
          } else {
            console.error(`离开房间失败: ${roomId}`)
            reject(new Error('离开房间失败'))
          }
          this.off('room_left', handler)
        }
      }

      this.on('room_left', handler)
      
      this.sendMessage({
        type: 'leave_room',
        room_id: roomId
      })

      // 设置超时
      setTimeout(() => {
        this.off('room_left', handler)
        reject(new Error('离开房间超时'))
      }, 5000)
    })
  }

  /**
   * 启动心跳机制
   */
  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected.value) {
        this.sendMessage({ type: 'heartbeat' })
        
        // 设置心跳超时
        this.heartbeatTimeout = setTimeout(() => {
          console.warn('心跳超时，尝试重连')
          this.reconnect()
        }, 30000) // 30秒超时
      }
    }, 60000) // 每分钟发送一次心跳
  }

  /**
   * 处理心跳响应
   */
  handleHeartbeatAck() {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout)
      this.heartbeatTimeout = null
    }
  }

  /**
   * 安排重连
   */
  scheduleReconnect() {
    this.reconnectAttempts++
    console.log(`第 ${this.reconnectAttempts} 次重连尝试...`)
    
    setTimeout(() => {
      if (this.reconnectAttempts <= this.maxReconnectAttempts) {
        this.connect([...this.rooms])
      }
    }, this.reconnectDelay * this.reconnectAttempts) // 指数退避
  }

  /**
   * 重新连接
   */
  reconnect() {
    if (this.ws) {
      this.ws.close()
    }
    this.connect([...this.rooms])
  }

  /**
   * 事件监听
   * @param {string} event - 事件类型
   * @param {Function} handler - 处理函数
   */
  on(event, handler) {
    if (!this.eventHandlers[event]) {
      this.eventHandlers[event] = []
    }
    this.eventHandlers[event].push(handler)
  }

  /**
   * 移除事件监听
   * @param {string} event - 事件类型
   * @param {Function} handler - 处理函数
   */
  off(event, handler) {
    if (this.eventHandlers[event]) {
      const index = this.eventHandlers[event].indexOf(handler)
      if (index > -1) {
        this.eventHandlers[event].splice(index, 1)
      }
    }
  }

  /**
   * 触发事件
   * @param {string} event - 事件类型
   * @param {any} data - 事件数据
   */
  emit(event, data) {
    if (this.eventHandlers[event]) {
      this.eventHandlers[event].forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          console.error(`事件处理错误 ${event}:`, error)
        }
      })
    }
  }

  /**
   * 获取连接状态
   */
  getStatus() {
    return {
      isConnected: this.isConnected.value,
      isConnecting: this.isConnecting.value,
      rooms: [...this.rooms],
      url: this.url,
      reconnectAttempts: this.reconnectAttempts
    }
  }
}

// 创建单例实例
const websocketClient = new WebSocketClient()

export default websocketClient