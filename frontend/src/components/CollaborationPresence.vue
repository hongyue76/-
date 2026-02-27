<template>
  <div class="collaboration-presence">
    <!-- 在线用户列表 -->
    <div class="online-users" v-if="onlineUsers.length > 0">
      <div class="users-header">
        <el-icon><User /></el-icon>
        <span>{{ onlineUsers.length }} 人在线</span>
      </div>
      <div class="user-list">
        <div 
          v-for="user in onlineUsers" 
          :key="user.user_id"
          class="user-item"
          :class="getUserStatusClass(user)"
        >
          <el-avatar :size="24" class="user-avatar">
            {{ user.username.charAt(0) }}
          </el-avatar>
          <span class="username">{{ user.username }}</span>
          <el-tag 
            v-if="user.current_task" 
            size="small" 
            type="warning"
            class="editing-tag"
          >
            编辑中
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 编辑状态指示器 -->
    <div class="editing-indicators">
      <transition-group name="indicator" tag="div">
        <div 
          v-for="indicator in activeIndicators" 
          :key="`${indicator.task_id}_${indicator.field_name}_${indicator.user_id}`"
          class="indicator-item"
        >
          <div class="indicator-content">
            <el-avatar :size="20" class="indicator-avatar">
              {{ indicator.username.charAt(0) }}
            </el-avatar>
            <div class="indicator-text">
              <span class="user-name">{{ indicator.username }}</span>
              <span class="action-text">
                正在编辑 {{ getFieldName(indicator.field_name) }}
                <span v-if="indicator.is_typing" class="typing-dot">●</span>
              </span>
            </div>
          </div>
          <div class="indicator-timer">
            {{ getTimeElapsed(indicator.start_time) }}
          </div>
        </div>
      </transition-group>
    </div>

    <!-- 字段级编辑提示 -->
    <div class="field-editing-notifications">
      <transition-group name="notification" tag="div">
        <div 
          v-for="notification in fieldNotifications" 
          :key="notification.id"
          class="field-notification"
          :class="notification.type"
        >
          <el-icon><Edit /></el-icon>
          <div class="notification-content">
            <strong>{{ notification.username }}</strong> 
            {{ notification.action }} {{ notification.field }}
          </div>
          <div class="notification-time">{{ notification.time }}</div>
        </div>
      </transition-group>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@vueuse/core'

const props = defineProps({
  listId: {
    type: Number,
    required: true
  }
})

// 状态数据
const onlineUsers = ref([])
const activeIndicators = ref([])
const fieldNotifications = ref([])

// WebSocket连接
const { data, send, close } = useWebSocket(
  `ws://localhost:8000/api/ws/collaboration/${props.listId}`,
  {
    autoReconnect: true,
    heartbeat: {
      message: JSON.stringify({ type: 'ping' }),
      interval: 30000,
    }
  }
)

// 计算属性
const getUserStatusClass = (user) => {
  return {
    'user-online': user.status === 'online',
    'user-idle': user.status === 'idle',
    'user-editing': user.current_task !== null
  }
}

const getFieldName = (field) => {
  const fieldNames = {
    'title': '标题',
    'description': '描述',
    'priority': '优先级',
    'completed': '完成状态',
    'due_date': '截止日期'
  }
  return fieldNames[field] || field
}

const getTimeElapsed = (startTime) => {
  const start = new Date(startTime)
  const now = new Date()
  const diff = Math.floor((now - start) / 1000)
  
  if (diff < 60) return `${diff}秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  return `${Math.floor(diff / 3600)}小时前`
}

// 方法
const handleWebSocketMessage = (message) => {
  try {
    const data = JSON.parse(message)
    
    switch (data.type) {
      case 'presence_change':
        updatePresence(data.users)
        break
      case 'editing_change':
        updateEditingIndicators(data.indicators)
        break
      case 'field_notification':
        showFieldNotification(data)
        break
    }
  } catch (error) {
    console.error('解析WebSocket消息失败:', error)
  }
}

const updatePresence = (users) => {
  onlineUsers.value = users.map(user => ({
    ...user,
    last_active: new Date(user.last_active)
  }))
}

const updateEditingIndicators = (indicators) => {
  activeIndicators.value = indicators.map(indicator => ({
    ...indicator,
    start_time: new Date(indicator.start_time)
  }))
}

const showFieldNotification = (notificationData) => {
  const notification = {
    id: Date.now(),
    ...notificationData,
    time: new Date().toLocaleTimeString()
  }
  
  fieldNotifications.value.push(notification)
  
  // 3秒后自动移除
  setTimeout(() => {
    const index = fieldNotifications.value.findIndex(n => n.id === notification.id)
    if (index > -1) {
      fieldNotifications.value.splice(index, 1)
    }
  }, 3000)
}

const sendEditingStart = (taskId, fieldName) => {
  send(JSON.stringify({
    type: 'start_editing',
    task_id: taskId,
    field_name: fieldName
  }))
}

const sendEditingStop = (taskId, fieldName) => {
  send(JSON.stringify({
    type: 'stop_editing',
    task_id: taskId,
    field_name: fieldName
  }))
}

const sendTypingStatus = (taskId, fieldName, isTyping) => {
  send(JSON.stringify({
    type: 'typing',
    task_id: taskId,
    field_name: fieldName,
    is_typing: isTyping
  }))
}

// 生命周期
onMounted(() => {
  if (data.value) {
    handleWebSocketMessage(data.value)
  }
})

onUnmounted(() => {
  close()
})

// 监听WebSocket数据
watch(data, (newData) => {
  if (newData) {
    handleWebSocketMessage(newData)
  }
})

// 暴露方法给父组件
defineExpose({
  sendEditingStart,
  sendEditingStop,
  sendTypingStatus
})
</script>

<style scoped>
.collaboration-presence {
  position: fixed;
  top: 60px;
  right: 20px;
  width: 300px;
  z-index: 1000;
  pointer-events: none;
}

.online-users {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 10px;
  pointer-events: auto;
}

.users-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 15px;
  border-bottom: 1px solid #ebeef5;
  font-weight: 500;
  color: #303133;
}

.user-list {
  max-height: 200px;
  overflow-y: auto;
}

.user-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 15px;
  border-bottom: 1px solid #f5f7fa;
  transition: background-color 0.2s;
}

.user-item:last-child {
  border-bottom: none;
}

.user-item:hover {
  background: #f5f7fa;
}

.user-avatar {
  background: #409eff;
  color: white;
  font-size: 12px;
}

.username {
  flex: 1;
  font-size: 14px;
  color: #303133;
}

.editing-tag {
  height: 20px;
  line-height: 18px;
}

.editing-indicators {
  pointer-events: auto;
}

.indicator-item {
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 8px;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.indicator-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.indicator-avatar {
  background: #67c23a;
  color: white;
  font-size: 10px;
}

.indicator-text {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-weight: 500;
  font-size: 12px;
  color: #303133;
}

.action-text {
  font-size: 11px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
}

.typing-dot {
  color: #409eff;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.indicator-timer {
  font-size: 10px;
  color: #c0c4cc;
}

.field-editing-notifications {
  pointer-events: auto;
}

.field-notification {
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 12px;
  margin-bottom: 8px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  animation: slideIn 0.3s ease-out;
}

.field-notification.enter-active {
  transition: all 0.3s ease;
}

.field-notification.leave-active {
  transition: all 0.3s ease;
  position: absolute;
}

.field-notification.enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.field-notification.leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.notification-content {
  flex: 1;
  font-size: 13px;
  color: #303133;
}

.notification-time {
  font-size: 11px;
  color: #909399;
  white-space: nowrap;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>