import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../utils/api'

export const useSharedListsStore = defineStore('sharedLists', () => {
  const sharedLists = ref([])
  const myLists = ref([])
  const loading = ref(false)

  const fetchMySharedLists = async () => {
    loading.value = true
    try {
      const response = await api.get('/shared-lists/')
      myLists.value = response.data
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '获取共享清单失败' 
      }
    } finally {
      loading.value = false
    }
  }

  const fetchJoinedLists = async () => {
    loading.value = true
    try {
      const response = await api.get('/shared-lists/member')
      sharedLists.value = response.data
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '获取参与清单失败' 
      }
    } finally {
      loading.value = false
    }
  }

  const createSharedList = async (listData) => {
    try {
      const response = await api.post('/shared-lists/', listData)
      myLists.value.push(response.data)
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '创建共享清单失败' 
      }
    }
  }

  const updateSharedList = async (listId, listData) => {
    try {
      const response = await api.put(`/shared-lists/${listId}`, listData)
      const index = myLists.value.findIndex(list => list.id === listId)
      if (index !== -1) {
        myLists.value[index] = response.data
      }
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '更新共享清单失败' 
      }
    }
  }

  const deleteSharedList = async (listId) => {
    try {
      await api.delete(`/shared-lists/${listId}`)
      myLists.value = myLists.value.filter(list => list.id !== listId)
      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '删除共享清单失败' 
      }
    }
  }

  const addMemberToList = async (listId, userId, role = 'member') => {
    try {
      const response = await api.post(`/shared-lists/${listId}/members/${userId}?role=${role}`)
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '添加成员失败' 
      }
    }
  }

  const removeMemberFromList = async (listId, userId) => {
    try {
      const response = await api.delete(`/shared-lists/${listId}/members/${userId}`)
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '移除成员失败' 
      }
    }
  }

  const updateMemberRole = async (listId, userId, role) => {
    try {
      const response = await api.put(`/shared-lists/${listId}/members/${userId}/role?role=${role}`)
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '更新成员角色失败' 
      }
    }
  }

  const getListMembers = async (listId) => {
    try {
      const response = await api.get(`/shared-lists/${listId}/members`)
      return { success: true, data: response.data }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '获取成员列表失败' 
      }
    }
  }

  return {
    sharedLists,
    myLists,
    loading,
    fetchMySharedLists,
    fetchJoinedLists,
    createSharedList,
    updateSharedList,
    deleteSharedList,
    addMemberToList,
    removeMemberFromList,
    updateMemberRole,
    getListMembers
  }
})