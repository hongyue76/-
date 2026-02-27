<template>
  <div class="comments-section">
    <div class="comments-header">
      <h3>评论 ({{ comments.length }})</h3>
      <el-button 
        v-if="!showCommentInput" 
        size="small" 
        @click="showCommentInput = true"
      >
        添加评论
      </el-button>
    </div>

    <!-- 添加评论输入框 -->
    <div v-if="showCommentInput" class="comment-input-section">
      <el-input
        v-model="newComment.content"
        type="textarea"
        :rows="3"
        placeholder="输入您的评论..."
        maxlength="500"
        show-word-limit
      />
      <div class="comment-actions">
        <el-button @click="cancelComment">取消</el-button>
        <el-button 
          type="primary" 
          @click="submitComment"
          :loading="submitting"
        >
          发布评论
        </el-button>
      </div>
    </div>

    <!-- 评论列表 -->
    <div class="comments-list">
      <div 
        v-for="comment in comments" 
        :key="comment.id" 
        class="comment-item"
      >
        <div class="comment-header">
          <div class="comment-author">
            <el-avatar :size="32">{{ comment.user.username.charAt(0).toUpperCase() }}</el-avatar>
            <span class="author-name">{{ comment.user.username }}</span>
          </div>
          <div class="comment-meta">
            <span class="comment-time">{{ formatTime(comment.created_at) }}</span>
            <div class="comment-actions">
              <el-button 
                v-if="canEditComment(comment)" 
                size="small" 
                type="text"
                @click="editComment(comment)"
              >
                编辑
              </el-button>
              <el-button 
                v-if="canDeleteComment(comment)" 
                size="small" 
                type="text"
                @click="deleteComment(comment)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
        
        <div v-if="editingCommentId === comment.id" class="edit-comment-section">
          <el-input
            v-model="editForm.content"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
          />
          <div class="comment-actions">
            <el-button @click="cancelEdit">取消</el-button>
            <el-button 
              type="primary" 
              @click="saveEdit(comment.id)"
              :loading="saving"
            >
              保存
            </el-button>
          </div>
        </div>
        
        <div v-else class="comment-content">
          {{ comment.content }}
        </div>
      </div>

      <div v-if="comments.length === 0" class="no-comments">
        <el-empty description="暂无评论" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useCommentsStore } from '../stores/comments'
import { useAuthStore } from '../stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'

const props = defineProps({
  todoId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['comment-added', 'comment-updated', 'comment-deleted'])

const commentsStore = useCommentsStore()
const authStore = useAuthStore()

const showCommentInput = ref(false)
const submitting = ref(false)
const saving = ref(false)
const editingCommentId = ref(null)

const newComment = reactive({
  content: ''
})

const editForm = reactive({
  content: ''
})

const comments = computed(() => {
  return commentsStore.comments[props.todoId] || []
})

watch(() => props.todoId, () => {
  loadComments()
}, { immediate: true })

const loadComments = async () => {
  if (props.todoId) {
    await commentsStore.getCommentsForTodo(props.todoId)
  }
}

const submitComment = async () => {
  if (!newComment.content.trim()) {
    ElMessage.warning('请输入评论内容')
    return
  }

  submitting.value = true
  try {
    const result = await commentsStore.addComment(props.todoId, newComment)
    if (result.success) {
      ElMessage.success('评论发布成功')
      newComment.content = ''
      showCommentInput.value = false
      emit('comment-added', result.data)
    } else {
      ElMessage.error(result.message)
    }
  } finally {
    submitting.value = false
  }
}

const cancelComment = () => {
  newComment.content = ''
  showCommentInput.value = false
}

const editComment = (comment) => {
  editingCommentId.value = comment.id
  editForm.content = comment.content
}

const saveEdit = async (commentId) => {
  if (!editForm.content.trim()) {
    ElMessage.warning('请输入评论内容')
    return
  }

  saving.value = true
  try {
    const result = await commentsStore.updateComment(commentId, editForm)
    if (result.success) {
      ElMessage.success('评论更新成功')
      editingCommentId.value = null
      emit('comment-updated', result.data)
    } else {
      ElMessage.error(result.message)
    }
  } finally {
    saving.value = false
  }
}

const cancelEdit = () => {
  editingCommentId.value = null
  editForm.content = ''
}

const deleteComment = async (comment) => {
  await ElMessageBox.confirm('确定要删除这条评论吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })

  const result = await commentsStore.deleteComment(comment.id, props.todoId)
  if (result.success) {
    ElMessage.success('评论删除成功')
    emit('comment-deleted', comment.id)
  } else {
    ElMessage.error(result.message)
  }
}

const canEditComment = (comment) => {
  return comment.user_id === authStore.user?.id
}

const canDeleteComment = (comment) => {
  return comment.user_id === authStore.user?.id
}

const formatTime = (dateString) => {
  if (!dateString) return ''
  
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date
  
  // 小于1分钟
  if (diff < 60000) {
    return '刚刚'
  }
  
  // 小于1小时
  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  }
  
  // 小于24小时
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  }
  
  // 显示具体日期
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.comments-section {
  border-top: 1px solid #ebeef5;
  padding-top: 20px;
  margin-top: 20px;
}

.comments-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.comments-header h3 {
  margin: 0;
  color: #303133;
}

.comment-input-section {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.comment-actions {
  margin-top: 10px;
  text-align: right;
}

.comment-item {
  padding: 15px 0;
  border-bottom: 1px solid #ebeef5;
}

.comment-item:last-child {
  border-bottom: none;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.comment-author {
  display: flex;
  align-items: center;
  gap: 10px;
}

.author-name {
  font-weight: 500;
  color: #303133;
}

.comment-meta {
  display: flex;
  align-items: center;
  gap: 15px;
}

.comment-time {
  color: #909399;
  font-size: 12px;
}

.comment-content {
  padding-left: 42px;
  line-height: 1.6;
  color: #606266;
}

.edit-comment-section {
  padding-left: 42px;
}

.no-comments {
  text-align: center;
  padding: 40px 0;
}
</style>