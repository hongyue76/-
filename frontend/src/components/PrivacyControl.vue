<template>
  <div class="privacy-control">
    <el-dialog
      v-model="showDialog"
      title="隐私设置"
      width="500px"
    >
      <div class="privacy-settings">
        <!-- 成员权限设置 -->
        <el-form :model="privacyForm" label-width="120px">
          <el-form-item label="默认权限">
            <el-select v-model="privacyForm.defaultPermission" @change="onDefaultPermissionChange">
              <el-option
                v-for="level in permissionLevels"
                :key="level.value"
                :label="level.label"
                :value="level.value"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="历史记录可见性">
            <el-select v-model="privacyForm.historyVisibility" @change="onHistoryVisibilityChange">
              <el-option
                v-for="visibility in visibilityOptions"
                :key="visibility.value"
                :label="visibility.label"
                :value="visibility.value"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="操作者匿名化">
            <el-switch
              v-model="privacyForm.anonymizeOperators"
              active-text="开启"
              inactive-text="关闭"
              @change="onAnonymizeChange"
            />
          </el-form-item>
        </el-form>
        
        <!-- 当前成员权限列表 -->
        <div class="member-permissions">
          <el-divider>成员权限管理</el-divider>
          <el-table :data="memberPermissions" style="width: 100%">
            <el-table-column prop="username" label="成员" width="120" />
            <el-table-column prop="currentPermission" label="当前权限">
              <template #default="{ row }">
                <el-tag :type="getPermissionTagType(row.currentPermission)">
                  {{ getPermissionLabel(row.currentPermission) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="历史可见性">
              <template #default="{ row }">
                <span>{{ getHistoryVisibilityText(row.currentPermission) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-dropdown @command="(command) => handlePermissionChange(row, command)">
                  <el-button size="small">
                    修改权限 <el-icon><arrow-down /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item 
                        v-for="level in availablePermissions" 
                        :key="level.value"
                        :command="level.value"
                        :disabled="level.value === row.currentPermission"
                      >
                        {{ level.label }}
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
            </el-table-column>
          </el-table>
        </div>
        
        <!-- 隐私说明 -->
        <div class="privacy-explanation">
          <el-alert
            title="隐私保护说明"
            type="info"
            :closable="false"
          >
            <template #default>
              <ul>
                <li><strong>所有者</strong>：可查看完整历史记录和操作者身份</li>
                <li><strong>管理员</strong>：可查看匿名化历史记录</li>
                <li><strong>编辑者/查看者</strong>：仅可查看任务变更概要</li>
                <li><strong>评论者</strong>：无法查看任何历史记录</li>
              </ul>
            </template>
          </el-alert>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="cancel">取消</el-button>
          <el-button type="primary" @click="save">保存设置</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: Boolean,
  sharedList: {
    type: Object,
    required: true
  },
  members: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'save'])

const showDialog = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 权限等级定义
const permissionLevels = [
  { value: 'owner', label: '所有者' },
  { value: 'admin', label: '管理员' },
  { value: 'editor', label: '编辑者' },
  { value: 'viewer', label: '查看者' },
  { value: 'commenter', label: '评论者' }
]

const visibilityOptions = [
  { value: 'full', label: '完整可见' },
  { value: 'anonymized', label: '匿名可见' },
  { value: 'summary', label: '概要可见' },
  { value: 'none', label: '不可见' }
]

// 表单数据
const privacyForm = ref({
  defaultPermission: 'viewer',
  historyVisibility: 'summary',
  anonymizeOperators: true
})

// 成员权限数据
const memberPermissions = ref([
  // 这里应该是从props.members转换而来
])

const availablePermissions = computed(() => {
  // 根据当前用户权限过滤可分配的权限等级
  return permissionLevels.filter(level => {
    // 实际应用中需要根据当前用户权限进行过滤
    return level.value !== 'owner' // 所有者权限不能分配给其他人
  })
})

// 方法
const getPermissionTagType = (permission) => {
  const typeMap = {
    'owner': 'danger',
    'admin': 'warning',
    'editor': 'primary',
    'viewer': 'success',
    'commenter': 'info'
  }
  return typeMap[permission] || 'default'
}

const getPermissionLabel = (permission) => {
  const labelMap = {
    'owner': '所有者',
    'admin': '管理员',
    'editor': '编辑者',
    'viewer': '查看者',
    'commenter': '评论者'
  }
  return labelMap[permission] || permission
}

const getHistoryVisibilityText = (permission) => {
  const visibilityMap = {
    'owner': '完整可见',
    'admin': '匿名可见',
    'editor': '概要可见',
    'viewer': '概要可见',
    'commenter': '不可见'
  }
  return visibilityMap[permission] || '未知'
}

const onDefaultPermissionChange = (value) => {
  console.log('默认权限变更:', value)
  // 可以添加验证逻辑
}

const onHistoryVisibilityChange = (value) => {
  console.log('历史可见性变更:', value)
}

const onAnonymizeChange = (value) => {
  console.log('匿名化设置变更:', value)
}

const handlePermissionChange = (member, newPermission) => {
  // 更新成员权限
  const index = memberPermissions.value.findIndex(m => m.id === member.id)
  if (index !== -1) {
    memberPermissions.value[index].currentPermission = newPermission
    ElMessage.success(`已将 ${member.username} 的权限修改为 ${getPermissionLabel(newPermission)}`)
  }
}

const save = () => {
  // 保存隐私设置
  const settings = {
    defaultPermission: privacyForm.value.defaultPermission,
    historyVisibility: privacyForm.value.historyVisibility,
    anonymizeOperators: privacyForm.value.anonymizeOperators,
    memberPermissions: memberPermissions.value.map(m => ({
      memberId: m.id,
      permission: m.currentPermission
    }))
  }
  
  emit('save', settings)
  ElMessage.success('隐私设置已保存')
  showDialog.value = false
}

const cancel = () => {
  // 取消操作，恢复原始设置
  showDialog.value = false
}

// 初始化数据
const initializeData = () => {
  // 从props初始化表单和成员数据
  if (props.sharedList && props.members) {
    // 设置默认值
    privacyForm.value.defaultPermission = props.sharedList.default_permission || 'viewer'
    privacyForm.value.historyVisibility = props.sharedList.history_visibility || 'summary'
    privacyForm.value.anonymizeOperators = props.sharedList.anonymize_operators || true
    
    // 初始化成员权限列表
    memberPermissions.value = props.members.map(member => ({
      id: member.id,
      username: member.username,
      currentPermission: member.permission || 'viewer'
    }))
  }
}

// 监听props变化
watch(() => props.sharedList, initializeData, { immediate: true })
watch(() => props.members, initializeData, { immediate: true })
</script>

<style scoped>
.privacy-settings {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.member-permissions {
  max-height: 300px;
  overflow-y: auto;
}

.privacy-explanation {
  margin-top: 20px;
}

.privacy-explanation ul {
  padding-left: 20px;
  margin: 10px 0;
}

.privacy-explanation li {
  margin: 5px 0;
  line-height: 1.5;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>