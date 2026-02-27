import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../utils/api'

export const useCommentsStore = defineStore('comments', () => {
  const comments = ref({})
  const loading = ref(false)

  const getCommentsForTodo = async (todoId) => {
    if (comments.value[todoId]) {
      return { success: true, data: comments.value[todoId] }
    }
    
    loading.value = true
    try {
      const response = await api.get(`/comments/todos/${todoId}`)
      comments.value[todoId] = response.data
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '获取评论失败' 
      }
    } finally {
      loading.value = false
    }
  }

  const addComment = async (todoId, commentData) => {
    try {
      const response = await api.post(`/comments/todos/${todoId}`, commentData)
      
      // 更新本地缓存
      if (!comments.value[todoId]) {
        comments.value[todoId] = []
      }
      comments.value[todoId].unshift(response.data)
      
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '添加评论失败' 
      }
    }
  }

  const updateComment = async (commentId, commentData) => {
    try {
      const response = await api.put(`/comments/${commentId}`, commentData)
      
      // 更新本地缓存
      Object.keys(comments.value).forEach(todoId => {
        const index = comments.value[todoId].findIndex(c => c.id === commentId)
        if (index !== -1) {
          comments.value[todoId][index] = response.data
        }
      })
      
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '更新评论失败' 
      }
    }
  }

  const deleteComment = async (commentId, todoId) => {
    try {
      await api.delete(`/comments/${commentId}`)
      
      // 从本地缓存中移除
      if (comments.value[todoId]) {
        comments.value[todoId] = comments.value[todoId].filter(c => c.id !== commentId)
      }
      
      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '删除评论失败' 
      }
    }
  }

  const clearComments = (todoId) => {
    if (todoId) {
      delete comments.value[todoId]
    } else {
      comments.value = {}
    }
  }

  return {
    comments,
    loading,
    getCommentsForTodo,
    addComment,
    updateComment,
    deleteComment,
    clearComments
  }
})