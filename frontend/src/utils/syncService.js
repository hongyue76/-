import api from './api'
import { localStorageService } from './localStorageService'

class SyncService {
  constructor() {
    this.syncInterval = null
    this.isSyncing = false
    this.maxRetries = 3
    this.retryDelay = 1000 // 1秒
    this.syncIntervalMs = 30000 // 30秒自动同步间隔
  }

  // 启动同步服务
  start() {
    // 立即执行一次同步
    this.sync()
    
    // 设置定期同步
    this.syncInterval = setInterval(() => {
      if (navigator.onLine) {
        this.sync()
      }
    }, this.syncIntervalMs)
    
    // 监听网络状态变化
    window.addEventListener('online', () => {
      console.log('网络连接恢复，开始同步...')
      this.sync()
    })
  }

  // 停止同步服务
  stop() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval)
      this.syncInterval = null
    }
  }

  // 执行同步
  async sync() {
    if (this.isSyncing || !navigator.onLine) {
      return
    }

    this.isSyncing = true
    
    try {
      // 1. 上传本地变更
      await this.uploadLocalChanges()
      
      // 2. 下载服务器最新数据
      await this.downloadServerChanges()
      
      // 3. 清理已同步的队列项
      await this.cleanupSyncQueue()
      
      console.log('数据同步完成')
    } catch (error) {
      console.error('同步过程中发生错误:', error)
    } finally {
      this.isSyncing = false
    }
  }

  // 上传本地变更到服务器
  async uploadLocalChanges() {
    const syncQueue = await localStorageService.getSyncQueue()
    const pendingItems = syncQueue.filter(item => 
      item.status === 'pending' || item.status === 'failed'
    )
    
    for (const item of pendingItems) {
      try {
        await this.processSyncItem(item)
        await localStorageService.updateSyncQueueItem(item.id, {
          status: 'synced',
          synced_at: new Date().toISOString()
        })
      } catch (error) {
        console.error(`同步项 ${item.id} 失败:`, error)
        await this.handleSyncFailure(item, error)
      }
    }
  }

  // 处理单个同步项
  async processSyncItem(item) {
    const { operation, storeName, data } = item
    
    switch (operation) {
      case 'create':
        return await this.createOnServer(storeName, data)
      case 'update':
        return await this.updateOnServer(storeName, data)
      case 'delete':
        return await this.deleteOnServer(storeName, data)
      default:
        throw new Error(`未知操作类型: ${operation}`)
    }
  }

  // 创建操作
  async createOnServer(storeName, data) {
    const endpoint = this.getEndpoint(storeName)
    const response = await api.post(endpoint, data)
    // 更新本地数据的服务器ID
    if (response.data.id && data.id !== response.data.id) {
      await this.updateLocalId(storeName, data.id, response.data.id)
    }
    return response.data
  }

  // 更新操作
  async updateOnServer(storeName, data) {
    const endpoint = this.getEndpoint(storeName)
    const response = await api.put(`${endpoint}/${data.id}`, data)
    return response.data
  }

  // 删除操作
  async deleteOnServer(storeName, data) {
    const endpoint = this.getEndpoint(storeName)
    await api.delete(`${endpoint}/${data.id}`)
    return { id: data.id, deleted: true }
  }

  // 更新本地ID映射
  async updateLocalId(storeName, oldId, newId) {
    // 获取原始数据
    let items
    if (localStorageService.isSupported) {
      items = await localStorageService.getAllFromIndexedDB(storeName)
    } else {
      items = await localStorageService.getAllFromLocalStorage(storeName)
    }
    
    const item = items.find(i => i.id === oldId)
    if (item) {
      item.id = newId
      item.server_id = newId
      if (localStorageService.isSupported) {
        await localStorageService.updateInIndexedDB(storeName, item)
      } else {
        await localStorageService.updateInLocalStorage(storeName, item)
      }
    }
  }

  // 处理同步失败
  async handleSyncFailure(item, error) {
    const retryCount = (item.retry_count || 0) + 1
    
    if (retryCount <= this.maxRetries) {
      // 增加重试延迟
      const delay = this.retryDelay * Math.pow(2, retryCount - 1)
      
      setTimeout(async () => {
        await localStorageService.updateSyncQueueItem(item.id, {
          status: 'pending',
          retry_count: retryCount,
          last_error: error.message,
          next_retry: new Date(Date.now() + delay).toISOString()
        })
      }, delay)
    } else {
      // 超过最大重试次数，标记为永久失败
      await localStorageService.updateSyncQueueItem(item.id, {
        status: 'failed_permanently',
        retry_count: retryCount,
        last_error: error.message
      })
    }
  }

  // 下载服务器最新数据
  async downloadServerChanges() {
    try {
      // 下载待办事项
      const todosResponse = await api.get('/todos/')
      await this.mergeServerData('todos', todosResponse.data)
      
      // 下载共享清单
      const listsResponse = await api.get('/shared-lists/')
      await this.mergeServerData('sharedLists', listsResponse.data)
      
      // 下载参与的清单
      const joinedListsResponse = await api.get('/shared-lists/member')
      await this.mergeServerData('sharedLists', joinedListsResponse.data)
      
    } catch (error) {
      console.error('下载服务器数据失败:', error)
      throw error
    }
  }

  // 合并服务器数据到本地
  async mergeServerData(storeName, serverData) {
    // 获取本地数据
    let localData
    if (localStorageService.isSupported) {
      localData = await localStorageService.getAllFromIndexedDB(storeName)
    } else {
      localData = await localStorageService.getAllFromLocalStorage(storeName)
    }
    
    // 创建映射以便快速查找
    const localMap = new Map(localData.map(item => [item.id, item]))
    const serverMap = new Map(serverData.map(item => [item.id, item]))
    
    // 处理服务器新增/更新的数据
    for (const [id, serverItem] of serverMap) {
      const localItem = localMap.get(id)
      
      if (!localItem) {
        // 新增数据
        await localStorageService.addItem(storeName, {
          ...serverItem,
          sync_status: 'synced',
          server_updated_at: serverItem.updated_at
        })
      } else {
        // 检查是否需要更新
        const localTime = new Date(localItem.local_updated_at || 0)
        const serverTime = new Date(serverItem.updated_at)
        
        if (serverTime > localTime) {
          // 服务器数据更新，需要合并
          const mergedItem = await this.resolveConflict(localItem, serverItem)
          await localStorageService.updateItem(storeName, {
            ...mergedItem,
            sync_status: 'synced',
            server_updated_at: serverItem.updated_at
          })
        }
      }
    }
    
    // 处理本地有但服务器没有的数据（可能被删除）
    for (const [id, localItem] of localMap) {
      if (!serverMap.has(id) && localItem.sync_status !== 'deleted') {
        // 服务器上不存在，但在本地存在
        // 这可能是本地新增的数据，需要上传
        if (localItem.sync_status === 'pending') {
          await localStorageService.addToSyncQueue({
            operation: 'create',
            storeName,
            data: localItem
          })
        }
      }
    }
  }

  // 冲突解决
  async resolveConflict(localItem, serverItem) {
    const localUpdateTime = new Date(localItem.local_updated_at || 0)
    const serverUpdateTime = new Date(serverItem.updated_at)
    
    // 简单的时间戳比较策略
    if (localUpdateTime > serverUpdateTime) {
      // 本地更新较新，保留本地版本
      console.log(`冲突解决: 保留本地版本 ${localItem.id}`)
      return {
        ...localItem,
        ...serverItem, // 合并服务器字段
        updated_at: localItem.local_updated_at
      }
    } else {
      // 服务器更新较新，采用服务器版本
      console.log(`冲突解决: 采用服务器版本 ${serverItem.id}`)
      return {
        ...serverItem,
        local_updated_at: localItem.local_updated_at
      }
    }
  }

  // 清理已同步的队列项
  async cleanupSyncQueue() {
    const cleanedCount = await localStorageService.clearSyncedItems()
    if (cleanedCount > 0) {
      console.log(`清理了 ${cleanedCount} 个已同步的队列项`)
    }
  }

  // 获取API端点
  getEndpoint(storeName) {
    const endpoints = {
      'todos': '/todos',
      'sharedLists': '/shared-lists',
      'comments': '/comments'
    }
    return endpoints[storeName] || `/${storeName}`
  }

  // 强制同步
  async forceSync() {
    if (this.isSyncing) {
      console.log('同步正在进行中...')
      return
    }
    
    console.log('开始强制同步...')
    await this.sync()
  }

  // 获取同步状态
  async getSyncStatus() {
    const syncQueue = await localStorageService.getSyncQueue()
    
    return {
      isSyncing: this.isSyncing,
      isOnline: navigator.onLine,
      pendingCount: syncQueue.filter(item => item.status === 'pending').length,
      failedCount: syncQueue.filter(item => 
        item.status === 'failed' || item.status === 'failed_permanently'
      ).length,
      syncedCount: syncQueue.filter(item => item.status === 'synced').length
    }
  }
}

// 创建单例实例
export const syncService = new SyncService()

// Vue composable
export function useSync() {
  return {
    syncService,
    startSync: () => syncService.start(),
    stopSync: () => syncService.stop(),
    forceSync: () => syncService.forceSync(),
    getSyncStatus: () => syncService.getSyncStatus()
  }
}