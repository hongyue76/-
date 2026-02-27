<template>
  <div class="conflict-card" :class="{ 'resolved': conflict.resolved }">
    <div class="conflict-header">
      <div class="conflict-title">
        <el-tag :type="getFieldTypeTag(conflict.field_name)" size="small">
          {{ getFieldDisplayName(conflict.field_name) }}
        </el-tag>
        <span class="field-label">{{ conflict.field_name }}</span>
      </div>
      <div class="conflict-actions">
        <el-button 
          size="small" 
          type="info" 
          @click="$emit('preview', conflict)"
        >
          预览
        </el-button>
      </div>
    </div>

    <div class="conflict-body">
      <!-- 时间轴视图 -->
      <div class="timeline-view">
        <div class="timeline-item server-item">
          <div class="timeline-dot server-dot"></div>
          <div class="timeline-content">
            <div class="timeline-header">
              <strong>服务器版本</strong>
              <span class="timestamp">{{ formatTime(conflict.server_timestamp) }}</span>
            </div>
            <div class="value-display">
              <ConflictValueDisplay 
                :value="conflict.server_value" 
                :field-type="conflict.field_name"
                variant="server"
              />
            </div>
          </div>
        </div>

        <div class="timeline-connector">
          <div class="conflict-marker">⚡ 冲突</div>
        </div>

        <div class="timeline-item client-item">
          <div class="timeline-dot client-dot"></div>
          <div class="timeline-content">
            <div class="timeline-header">
              <strong>您的版本</strong>
              <span class="timestamp">{{ formatTime(conflict.client_timestamp) }}</span>
            </div>
            <div class="value-display">
              <ConflictValueDisplay 
                :value="conflict.client_new_value" 
                :field-type="conflict.field_name"
                variant="client"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 解决方案选择 -->
      <div class="resolution-panel" v-if="!conflict.resolved">
        <el-divider>选择解决方案</el-divider>
        <div class="resolution-options">
          <el-radio-group v-model="selectedResolution" @change="onResolutionChange">
            <div class="resolution-option">
              <el-radio label="server_wins" border>
                <div class="option-content">
                  <div class="option-title">采用服务器版本</div>
                  <div class="option-preview">
                    <ConflictValueDisplay 
                      :value="conflict.server_value" 
                      :field-type="conflict.field_name"
                      size="small"
                    />
                  </div>
                </div>
              </el-radio>
            </div>

            <div class="resolution-option">
              <el-radio label="client_wins" border>
                <div class="option-content">
                  <div class="option-title">保留我的修改</div>
                  <div class="option-preview">
                    <ConflictValueDisplay 
                      :value="conflict.client_new_value" 
                      :field-type="conflict.field_name"
                      size="small"
                    />
                  </div>
                </div>
              </el-radio>
            </div>

            <div class="resolution-option" v-if="canMerge">
              <el-radio label="smart_merge" border>
                <div class="option-content">
                  <div class="option-title">智能合并</div>
                  <div class="option-preview">
                    <ConflictValueDisplay 
                      :value="getMergedValue()" 
                      :field-type="conflict.field_name"
                      size="small"
                    />
                  </div>
                </div>
              </el-radio>
            </div>
          </el-radio-group>
        </div>
      </div>

      <!-- 已解决状态 -->
      <div class="resolved-status" v-else>
        <el-result 
          icon="success" 
          title="已解决" 
          :sub-title="`解决方案: ${getResolutionText()}`"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import ConflictValueDisplay from './ConflictValueDisplay.vue'

const props = defineProps({
  conflict: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['resolve', 'preview'])

const selectedResolution = ref('')

const canMerge = computed(() => {
  const mergeableTypes = ['title', 'description', 'content']
  return mergeableTypes.includes(props.conflict.field_name)
})

const onResolutionChange = (value) => {
  const resolution = {
    type: value,
    data: value === 'smart_merge' ? { merged: getMergedValue() } : null
  }
  emit('resolve', props.conflict.id, resolution)
}

const getMergedValue = () => {
  if (!canMerge.value) return props.conflict.server_value
  
  switch(props.conflict.field_name) {
    case 'title':
    case 'description':
      return `${props.conflict.server_value} & ${props.conflict.client_new_value}`
    default:
      return props.conflict.server_value
  }
}

const getFieldTypeTag = (fieldName) => {
  const typeMap = {
    'title': 'primary',
    'description': 'success',
    'priority': 'warning',
    'completed': 'info',
    'due_date': 'danger'
  }
  return typeMap[fieldName] || 'default'
}

const getFieldDisplayName = (fieldName) => {
  const displayNameMap = {
    'title': '标题',
    'description': '描述',
    'priority': '优先级',
    'completed': '完成状态',
    'due_date': '截止日期'
  }
  return displayNameMap[fieldName] || fieldName
}

const formatTime = (timestamp) => {
  if (!timestamp) return '未知时间'
  return new Date(timestamp).toLocaleString('zh-CN')
}

const getResolutionText = () => {
  // 这里可以根据实际的解决记录来显示
  return '手动选择'
}
</script>

<style scoped>
.conflict-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 15px;
  transition: all 0.3s;
}

.conflict-card:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.conflict-card.resolved {
  border-color: #67c23a;
  background: #f0f9ff;
}

.conflict-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}

.conflict-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.field-label {
  font-weight: 500;
  color: #303133;
}

.conflict-body {
  padding: 20px;
}

.timeline-view {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.timeline-item {
  display: flex;
  gap: 15px;
  align-items: flex-start;
}

.timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 8px;
}

.server-dot {
  background: #409eff;
}

.client-dot {
  background: #e6a23c;
}

.timeline-content {
  flex: 1;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.timestamp {
  font-size: 12px;
  color: #909399;
}

.timeline-connector {
  display: flex;
  justify-content: center;
  position: relative;
}

.timeline-connector::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #dcdfe6;
}

.conflict-marker {
  background: #f56c6c;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  z-index: 1;
}

.resolution-panel {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 6px;
}

.resolution-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.resolution-option {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
}

.option-content {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.option-title {
  font-weight: 500;
  color: #303133;
}

.option-preview {
  font-size: 12px;
  color: #606266;
}

.resolved-status {
  text-align: center;
}
</style>