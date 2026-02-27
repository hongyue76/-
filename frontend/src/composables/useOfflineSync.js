import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { offlineSyncService } from '@/services/offlineSync'

// 冲突状态管理
const conflicts = ref([])
const isLoading = ref(false)

export function useOfflineSync() {
  // 获取冲突列表
  const loadConflicts = async () => {
    try {
      isLoading.value = true
      const response = await offlineSyncService.getPendingConflicts()
      conflicts.value = response.data || []
    } catch (error) {
      ElMessage.error('加载冲突列表失败')
      console.error('加载冲突失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  // 解决单个冲突
  const resolveConflict = async (conflictId, resolution) => {
    try {
      await offlineSyncService.resolveConflict(conflictId, resolution)
      
      // 从本地列表中移除已解决的冲突
      conflicts.value = conflicts.value.filter(c => c.id !== conflictId)
      
      ElMessage.success('冲突已解决')
      return true
    } catch (error) {
      ElMessage.error('解决冲突失败')
      console.error('解决冲突失败:', error)
      return false
    }
  }

  // 批量解决冲突
  const resolveMultipleConflicts = async (resolutions) => {
    try {
      isLoading.value = true
      const results = await Promise.allSettled(
        resolutions.map(({ conflictId, resolution }) => 
          resolveConflict(conflictId, resolution)
        )
      )
      
      const successful = results.filter(result => result.status === 'fulfilled' && result.value)
      const failed = results.filter(result => result.status === 'rejected' || !result.value)
      
      if (successful.length > 0) {
        ElMessage.success(`成功解决 ${successful.length} 个冲突`)
      }
      
      if (failed.length > 0) {
        ElMessage.warning(`${failed.length} 个冲突解决失败`)
      }
      
      return {
        successful: successful.length,
        failed: failed.length
      }
    } catch (error) {
      ElMessage.error('批量解决冲突时发生错误')
      return { successful: 0, failed: resolutions.length }
    } finally {
      isLoading.value = false
    }
  }

  // 获取冲突统计
  const conflictStats = computed(() => ({
    total: conflicts.value.length,
    byField: groupConflictsByField(conflicts.value),
    byTask: groupConflictsByTask(conflicts.value),
    unresolved: conflicts.value.filter(c => !c.resolved).length
  }))

  // 按字段分组冲突
  const groupConflictsByField = (conflictList) => {
    const groups = {}
    conflictList.forEach(conflict => {
      const field = conflict.field_name
      if (!groups[field]) {
        groups[field] = []
      }
      groups[field].push(conflict)
    })
    return groups
  }

  // 按任务分组冲突
  const groupConflictsByTask = (conflictList) => {
    const groups = {}
    conflictList.forEach(conflict => {
      const taskId = conflict.todo_id
      if (!groups[taskId]) {
        groups[taskId] = []
      }
      groups[taskId].push(conflict)
    })
    return groups
  }

  // 获取推荐解决策略
  const getRecommendedResolution = (conflict) => {
    // 基于冲突类型和上下文给出推荐
    const fieldWeights = {
      'title': 0.8,
      'description': 0.6,
      'priority': 0.4,
      'completed': 0.9,
      'due_date': 0.7
    }
    
    const timeDifference = new Date(conflict.server_timestamp) - new Date(conflict.client_timestamp)
    const fieldWeight = fieldWeights[conflict.field_name] || 0.5
    
    // 如果服务器版本更新且字段重要性高，推荐服务器版本
    if (timeDifference > 0 && fieldWeight > 0.7) {
      return 'server_wins'
    }
    
    // 如果客户端修改较新，推荐客户端版本
    if (timeDifference < 0) {
      return 'client_wins'
    }
    
    // 对于可合并的字段，推荐智能合并
    const mergeableFields = ['title', 'description', 'content']
    if (mergeableFields.includes(conflict.field_name)) {
      return 'smart_merge'
    }
    
    // 默认推荐服务器版本
    return 'server_wins'
  }

  // 自动解决简单冲突
  const autoResolveSimpleConflicts = async () => {
    const simpleConflicts = conflicts.value.filter(conflict => {
      // 简单冲突条件：时间差很小且字段不重要
      const timeDiff = Math.abs(
        new Date(conflict.server_timestamp) - new Date(conflict.client_timestamp)
      )
      const simpleFields = ['category', 'tags']
      return timeDiff < 300000 && simpleFields.includes(conflict.field_name)
    })

    if (simpleConflicts.length === 0) {
      return { resolved: 0, skipped: conflicts.value.length }
    }

    const resolutions = simpleConflicts.map(conflict => ({
      conflictId: conflict.id,
      resolution: {
        type: 'smart_merge',
        data: {
          merged: `${conflict.server_value} & ${conflict.client_new_value}`
        }
      }
    }))

    const result = await resolveMultipleConflicts(resolutions)
    
    ElMessage.info(`自动解决了 ${result.successful} 个简单冲突`)
    
    return result
  }

  return {
    // 状态
    conflicts: computed(() => conflicts.value),
    isLoading: computed(() => isLoading.value),
    conflictStats,
    
    // 方法
    loadConflicts,
    resolveConflict,
    resolveMultipleConflicts,
    getRecommendedResolution,
    autoResolveSimpleConflicts,
    
    // 工具方法
    groupConflictsByField,
    groupConflictsByTask
  }
}

// 冲突检测hook
export function useConflictDetection() {
  const detectedConflicts = ref([])
  
  const detectConflicts = (localChanges, serverChanges) => {
    const conflicts = []
    
    // 检测字段级别的冲突
    localChanges.forEach(localChange => {
      const serverChange = serverChanges.find(sc => 
        sc.todo_id === localChange.todo_id && 
        sc.field_name === localChange.field_name
      )
      
      if (serverChange && serverChange.timestamp > localChange.timestamp) {
        conflicts.push({
          id: `${localChange.todo_id}-${localChange.field_name}`,
          todo_id: localChange.todo_id,
          field_name: localChange.field_name,
          local_value: localChange.new_value,
          server_value: serverChange.new_value,
          local_timestamp: localChange.timestamp,
          server_timestamp: serverChange.timestamp,
          severity: calculateSeverity(localChange.field_name)
        })
      }
    })
    
    detectedConflicts.value = conflicts
    return conflicts
  }
  
  const calculateSeverity = (fieldName) => {
    const severityMap = {
      'title': 'high',
      'description': 'medium',
      'priority': 'medium',
      'completed': 'critical',
      'due_date': 'high'
    }
    return severityMap[fieldName] || 'low'
  }
  
  return {
    detectedConflicts: computed(() => detectedConflicts.value),
    detectConflicts
  }
}