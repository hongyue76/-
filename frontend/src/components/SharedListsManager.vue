<template>
  <div class="shared-lists-manager">
    <el-tabs v-model="activeTab">
      <!-- 我创建的清单 -->
      <el-tab-pane label="我创建的" name="myLists">
        <div class="tab-content">
          <div class="header-actions">
            <el-button type="primary" @click="showCreateDialog = true">
              <el-icon><Plus /></el-icon>
              创建共享清单
            </el-button>
          </div>
          
          <el-table :data="sharedListsStore.myLists" v-loading="sharedListsStore.loading">
            <el-table-column prop="name" label="清单名称" width="200" />
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="scope">
                {{ formatDate(scope.row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="成员数量" width="100">
              <template #default="scope">
                <el-tag>{{ getMemberCount(scope.row.id) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="scope">
                <el-button size="small" @click="manageMembers(scope.row)">管理成员</el-button>
                <el-button size="small" type="primary" @click="editList(scope.row)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteList(scope.row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 我参与的清单 -->
      <el-tab-pane label="我参与的" name="joinedLists">
        <div class="tab-content">
          <el-table :data="sharedListsStore.sharedLists" v-loading="sharedListsStore.loading">
            <el-table-column prop="name" label="清单名称" width="200" />
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="owner.username" label="创建者" width="120" />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="scope">
                {{ formatDate(scope.row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="我的角色" width="100">
              <template #default="scope">
                <el-tag :type="getRoleTagType(getMyRole(scope.row.id))">
                  {{ getMyRole(scope.row.id) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button size="small" @click="viewListDetails(scope.row)">查看详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 创建/编辑清单对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingList ? '编辑共享清单' : '创建共享清单'"
      width="500px"
    >
      <el-form :model="listForm" :rules="listRules" ref="listFormRef" label-width="80px">
        <el-form-item label="清单名称" prop="name">
          <el-input v-model="listForm.name" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input type="textarea" v-model="listForm.description" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="submitListForm">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 成员管理对话框 -->
    <el-dialog
      v-model="showMembersDialog"
      title="成员管理"
      width="600px"
    >
      <div v-if="currentList">
        <h3>{{ currentList.name }} - 成员列表</h3>
        
        <!-- 添加成员 -->
        <div class="add-member-section">
          <el-input
            v-model="newMember.userId"
            placeholder="输入用户ID"
            style="width: 200px; margin-right: 10px;"
          />
          <el-select v-model="newMember.role" placeholder="选择角色" style="width: 120px; margin-right: 10px;">
            <el-option label="成员" value="member" />
            <el-option label="管理员" value="admin" />
          </el-select>
          <el-button type="primary" @click="addMember">添加成员</el-button>
        </div>

        <!-- 成员列表 -->
        <el-table :data="currentMembers" style="margin-top: 20px;">
          <el-table-column prop="user.username" label="用户名" />
          <el-table-column prop="role" label="角色">
            <template #default="scope">
              <el-tag :type="getRoleTagType(scope.row.role)">
                {{ scope.row.role }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="joined_at" label="加入时间">
            <template #default="scope">
              {{ formatDate(scope.row.joined_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="scope">
              <el-button 
                v-if="scope.row.role !== 'owner'" 
                size="small" 
                @click="changeMemberRole(scope.row)"
              >
                更改角色
              </el-button>
              <el-button 
                v-if="scope.row.role !== 'owner'" 
                size="small" 
                type="danger"
                @click="removeMember(scope.row.user_id)"
              >
                移除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useSharedListsStore } from '../stores/sharedLists'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const sharedListsStore = useSharedListsStore()
const activeTab = ref('myLists')
const showCreateDialog = ref(false)
const showMembersDialog = ref(false)
const editingList = ref(null)
const currentList = ref(null)
const currentMembers = ref([])
const listFormRef = ref()

const listForm = reactive({
  name: '',
  description: ''
})

const newMember = reactive({
  userId: '',
  role: 'member'
})

const listRules = {
  name: [{ required: true, message: '请输入清单名称', trigger: 'blur' }]
}

onMounted(() => {
  loadSharedLists()
})

const loadSharedLists = async () => {
  await sharedListsStore.fetchMySharedLists()
  await sharedListsStore.fetchJoinedLists()
}

const formatDate = (dateString) => {
  if (!dateString) return '无'
  return new Date(dateString).toLocaleString('zh-CN')
}

const getMemberCount = (listId) => {
  // 这里应该调用API获取实际成员数量
  return 'N/A'
}

const getMyRole = (listId) => {
  // 这里应该返回当前用户在此清单中的角色
  return 'member'
}

const getRoleTagType = (role) => {
  const types = {
    owner: 'danger',
    admin: 'warning',
    member: 'success'
  }
  return types[role] || 'info'
}

const submitListForm = async () => {
  if (!listFormRef.value) return
  
  await listFormRef.value.validate(async (valid) => {
    if (valid) {
      let result
      if (editingList.value) {
        result = await sharedListsStore.updateSharedList(editingList.value.id, listForm)
      } else {
        result = await sharedListsStore.createSharedList(listForm)
      }
      
      if (result.success) {
        ElMessage.success(editingList.value ? '更新成功' : '创建成功')
        showCreateDialog.value = false
        resetListForm()
        loadSharedLists()
      } else {
        ElMessage.error(result.message)
      }
    }
  })
}

const editList = (list) => {
  editingList.value = list
  Object.assign(listForm, {
    name: list.name,
    description: list.description
  })
  showCreateDialog.value = true
}

const deleteList = async (listId) => {
  await ElMessageBox.confirm('确定要删除这个共享清单吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
  
  const result = await sharedListsStore.deleteSharedList(listId)
  if (result.success) {
    ElMessage.success('删除成功')
    loadSharedLists()
  } else {
    ElMessage.error(result.message)
  }
}

const manageMembers = async (list) => {
  currentList.value = list
  const result = await sharedListsStore.getListMembers(list.id)
  if (result.success) {
    currentMembers.value = result.data
    showMembersDialog.value = true
  } else {
    ElMessage.error(result.message)
  }
}

const addMember = async () => {
  if (!newMember.userId) {
    ElMessage.warning('请输入用户ID')
    return
  }
  
  const result = await sharedListsStore.addMemberToList(
    currentList.value.id, 
    parseInt(newMember.userId), 
    newMember.role
  )
  
  if (result.success) {
    ElMessage.success('成员添加成功')
    newMember.userId = ''
    // 重新加载成员列表
    const membersResult = await sharedListsStore.getListMembers(currentList.value.id)
    if (membersResult.success) {
      currentMembers.value = membersResult.data
    }
  } else {
    ElMessage.error(result.message)
  }
}

const removeMember = async (userId) => {
  await ElMessageBox.confirm('确定要移除这个成员吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
  
  const result = await sharedListsStore.removeMemberFromList(currentList.value.id, userId)
  if (result.success) {
    ElMessage.success('成员移除成功')
    currentMembers.value = currentMembers.value.filter(m => m.user_id !== userId)
  } else {
    ElMessage.error(result.message)
  }
}

const changeMemberRole = async (member) => {
  const newRole = member.role === 'member' ? 'admin' : 'member'
  const result = await sharedListsStore.updateMemberRole(currentList.value.id, member.user_id, newRole)
  if (result.success) {
    ElMessage.success('角色更新成功')
    member.role = newRole
  } else {
    ElMessage.error(result.message)
  }
}

const viewListDetails = (list) => {
  // 跳转到清单详情页面
  console.log('查看清单详情:', list)
}

const resetListForm = () => {
  editingList.value = null
  Object.assign(listForm, {
    name: '',
    description: ''
  })
  if (listFormRef.value) {
    listFormRef.value.resetFields()
  }
}
</script>

<style scoped>
.shared-lists-manager {
  padding: 20px;
}

.tab-content {
  margin-top: 20px;
}

.header-actions {
  margin-bottom: 20px;
  text-align: right;
}

.add-member-section {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}
</style>