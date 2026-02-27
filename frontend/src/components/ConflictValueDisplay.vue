<template>
  <div class="value-display" :class="[variant, size]">
    <template v-if="fieldType === 'completed'">
      <el-tag :type="value ? 'success' : 'info'" size="small">
        {{ value ? '已完成' : '未完成' }}
      </el-tag>
    </template>
    
    <template v-else-if="fieldType === 'priority'">
      <el-tag :type="getPriorityType(value)" size="small">
        {{ getPriorityText(value) }}
      </el-tag>
    </template>
    
    <template v-else-if="fieldType === 'due_date'">
      <el-tag v-if="value" type="warning" size="small">
        {{ formatDate(value) }}
      </el-tag>
      <el-tag v-else type="info" size="small">无截止日期</el-tag>
    </template>
    
    <template v-else-if="fieldType === 'title' || fieldType === 'description'">
      <div class="text-value" :title="value">
        {{ truncateText(value, maxLength) }}
      </div>
    </template>
    
    <template v-else>
      <div class="text-value" :title="value">
        {{ truncateText(String(value), maxLength) }}
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: {
    type: [String, Boolean, Number, Date],
    default: ''
  },
  fieldType: {
    type: String,
    default: 'text'
  },
  variant: {
    type: String,
    default: 'default', // 'server' | 'client' | 'default'
    validator: (value) => ['server', 'client', 'default'].includes(value)
  },
  size: {
    type: String,
    default: 'normal', // 'small' | 'normal' | 'large'
    validator: (value) => ['small', 'normal', 'large'].includes(value)
  }
})

const maxLength = computed(() => {
  const lengths = {
    small: 30,
    normal: 100,
    large: 200
  }
  return lengths[props.size] || lengths.normal
})

const getPriorityType = (priority) => {
  const typeMap = {
    'HIGH': 'danger',
    'MEDIUM': 'warning', 
    'LOW': 'success'
  }
  return typeMap[priority] || 'info'
}

const getPriorityText = (priority) => {
  const textMap = {
    'HIGH': '高优先级',
    'MEDIUM': '中优先级',
    'LOW': '低优先级'
  }
  return textMap[priority] || priority
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}
</script>

<style scoped>
.value-display {
  display: inline-block;
}

.value-display.server {
  border-left: 3px solid #409eff;
  padding-left: 8px;
}

.value-display.client {
  border-left: 3px solid #e6a23c;
  padding-left: 8px;
}

.value-display.small {
  font-size: 12px;
}

.value-display.normal {
  font-size: 14px;
}

.value-display.large {
  font-size: 16px;
}

.text-value {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* 特殊样式 */
.value-display.server .text-value {
  color: #409eff;
}

.value-display.client .text-value {
  color: #e6a23c;
}
</style>