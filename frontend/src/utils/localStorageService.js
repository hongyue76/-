import { ref } from 'vue'

class LocalStorageService {
  constructor() {
    this.dbName = 'todoAppDB'
    this.version = 1
    this.db = null
    this.isSupported = typeof window !== 'undefined' && !!window.indexedDB
  }

  // 初始化数据库
  async init() {
    if (!this.isSupported) {
      console.warn('IndexedDB not supported, falling back to localStorage')
      return this.initLocalStorageFallback()
    }

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version)
      
      request.onerror = () => reject(request.error)
      
      request.onsuccess = () => {
        this.db = request.result
        resolve(this.db)
      }
      
      request.onupgradeneeded = (event) => {
        const db = event.target.result
        
        // 创建对象存储
        if (!db.objectStoreNames.contains('todos')) {
          const todoStore = db.createObjectStore('todos', { keyPath: 'id' })
          todoStore.createIndex('user_id', 'user_id', { unique: false })
          todoStore.createIndex('updated_at', 'updated_at', { unique: false })
        }
        
        if (!db.objectStoreNames.contains('sharedLists')) {
          const listStore = db.createObjectStore('sharedLists', { keyPath: 'id' })
          listStore.createIndex('owner_id', 'owner_id', { unique: false })
        }
        
        if (!db.objectStoreNames.contains('comments')) {
          const commentStore = db.createObjectStore('comments', { keyPath: 'id' })
          commentStore.createIndex('todo_id', 'todo_id', { unique: false })
        }
        
        if (!db.objectStoreNames.contains('syncQueue')) {
          const queueStore = db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true })
          queueStore.createIndex('timestamp', 'timestamp', { unique: false })
          queueStore.createIndex('status', 'status', { unique: false })
        }
      }
    })
  }

  // localStorage 备用方案
  initLocalStorageFallback() {
    this.storage = window.localStorage
    return Promise.resolve(true)
  }

  // 通用数据操作方法
  async addItem(storeName, item) {
    if (!this.db) await this.init()
    
    const itemWithTimestamp = {
      ...item,
      local_updated_at: new Date().toISOString(),
      sync_status: 'pending'
    }
    
    if (this.isSupported) {
      return this.addToIndexedDB(storeName, itemWithTimestamp)
    } else {
      return this.addToLocalStorage(storeName, itemWithTimestamp)
    }
  }

  async updateItem(storeName, item) {
    if (!this.db) await this.init()
    
    const itemWithTimestamp = {
      ...item,
      local_updated_at: new Date().toISOString(),
      sync_status: 'modified'
    }
    
    if (this.isSupported) {
      return this.updateInIndexedDB(storeName, itemWithTimestamp)
    } else {
      return this.updateInLocalStorage(storeName, itemWithTimestamp)
    }
  }

  async deleteItem(storeName, id) {
    if (!this.db) await this.init()
    
    const deleteRecord = {
      id,
      deleted_at: new Date().toISOString(),
      sync_status: 'deleted'
    }
    
    if (this.isSupported) {
      return this.deleteFromIndexedDB(storeName, id, deleteRecord)
    } else {
      return this.deleteFromLocalStorage(storeName, id, deleteRecord)
    }
  }

  async getAllItems(storeName, userId = null) {
    if (!this.db) await this.init()
    
    if (this.isSupported) {
      return this.getAllFromIndexedDB(storeName, userId)
    } else {
      return this.getAllFromLocalStorage(storeName, userId)
    }
  }

  // IndexedDB 操作方法
  addToIndexedDB(storeName, item) {
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.add(item)
      
      request.onsuccess = () => resolve(item)
      request.onerror = () => reject(request.error)
    })
  }

  updateInIndexedDB(storeName, item) {
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.put(item)
      
      request.onsuccess = () => resolve(item)
      request.onerror = () => reject(request.error)
    })
  }

  deleteFromIndexedDB(storeName, id, deleteRecord) {
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite')
      const store = transaction.objectStore(storeName)
      
      // 先获取原始数据用于同步队列
      const getRequest = store.get(id)
      getRequest.onsuccess = () => {
        const originalItem = getRequest.result
        if (originalItem) {
          // 添加到同步队列
          this.addToSyncQueue({
            operation: 'delete',
            storeName,
            data: { ...originalItem, ...deleteRecord }
          })
        }
        
        // 执行删除
        const deleteRequest = store.delete(id)
        deleteRequest.onsuccess = () => resolve(deleteRecord)
        deleteRequest.onerror = () => reject(deleteRequest.error)
      }
    })
  }

  getAllFromIndexedDB(storeName, userId = null) {
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly')
      const store = transaction.objectStore(storeName)
      
      let request
      if (userId) {
        const index = store.index('user_id')
        request = index.getAll(IDBKeyRange.only(userId))
      } else {
        request = store.getAll()
      }
      
      request.onsuccess = () => resolve(request.result.filter(item => !item.deleted_at))
      request.onerror = () => reject(request.error)
    })
  }

  // localStorage 操作方法
  addToLocalStorage(storeName, item) {
    try {
      const key = `${storeName}_${item.id}`
      const existing = this.storage.getItem(key)
      
      if (existing) {
        throw new Error('Item already exists')
      }
      
      this.storage.setItem(key, JSON.stringify(item))
      
      // 添加到同步队列
      this.addToSyncQueue({
        operation: 'create',
        storeName,
        data: item
      })
      
      return Promise.resolve(item)
    } catch (error) {
      return Promise.reject(error)
    }
  }

  updateInLocalStorage(storeName, item) {
    try {
      const key = `${storeName}_${item.id}`
      const existing = this.storage.getItem(key)
      
      if (!existing) {
        throw new Error('Item not found')
      }
      
      this.storage.setItem(key, JSON.stringify(item))
      
      // 添加到同步队列
      this.addToSyncQueue({
        operation: 'update',
        storeName,
        data: item
      })
      
      return Promise.resolve(item)
    } catch (error) {
      return Promise.reject(error)
    }
  }

  deleteFromLocalStorage(storeName, id, deleteRecord) {
    try {
      const key = `${storeName}_${id}`
      const existing = this.storage.getItem(key)
      
      if (existing) {
        const originalItem = JSON.parse(existing)
        // 添加到同步队列
        this.addToSyncQueue({
          operation: 'delete',
          storeName,
          data: { ...originalItem, ...deleteRecord }
        })
        
        this.storage.removeItem(key)
      }
      
      return Promise.resolve(deleteRecord)
    } catch (error) {
      return Promise.reject(error)
    }
  }

  getAllFromLocalStorage(storeName, userId = null) {
    try {
      const items = []
      for (let i = 0; i < this.storage.length; i++) {
        const key = this.storage.key(i)
        if (key.startsWith(`${storeName}_`)) {
          const item = JSON.parse(this.storage.getItem(key))
          if (!item.deleted_at && (!userId || item.user_id === userId)) {
            items.push(item)
          }
        }
      }
      return Promise.resolve(items)
    } catch (error) {
      return Promise.reject(error)
    }
  }

  // 同步队列管理
  async addToSyncQueue(operation) {
    const syncItem = {
      ...operation,
      id: Date.now() + Math.random(),
      timestamp: new Date().toISOString(),
      status: 'pending',
      retry_count: 0
    }
    
    if (this.isSupported) {
      return this.addToIndexedDB('syncQueue', syncItem)
    } else {
      const queue = JSON.parse(this.storage.getItem('syncQueue') || '[]')
      queue.push(syncItem)
      this.storage.setItem('syncQueue', JSON.stringify(queue))
      return Promise.resolve(syncItem)
    }
  }

  async getSyncQueue() {
    if (this.isSupported) {
      return this.getAllFromIndexedDB('syncQueue')
    } else {
      return Promise.resolve(JSON.parse(this.storage.getItem('syncQueue') || '[]'))
    }
  }

  async updateSyncQueueItem(id, updates) {
    if (this.isSupported) {
      const transaction = this.db.transaction(['syncQueue'], 'readwrite')
      const store = transaction.objectStore('syncQueue')
      const request = store.get(id)
      
      return new Promise((resolve, reject) => {
        request.onsuccess = () => {
          const item = request.result
          if (item) {
            Object.assign(item, updates)
            const updateRequest = store.put(item)
            updateRequest.onsuccess = () => resolve(item)
            updateRequest.onerror = () => reject(updateRequest.error)
          } else {
            reject(new Error('Sync queue item not found'))
          }
        }
        request.onerror = () => reject(request.error)
      })
    } else {
      const queue = JSON.parse(this.storage.getItem('syncQueue') || '[]')
      const index = queue.findIndex(item => item.id === id)
      if (index !== -1) {
        Object.assign(queue[index], updates)
        this.storage.setItem('syncQueue', JSON.stringify(queue))
        return Promise.resolve(queue[index])
      }
      return Promise.reject(new Error('Sync queue item not found'))
    }
  }

  // 清理已同步的数据
  async clearSyncedItems() {
    if (this.isSupported) {
      const transaction = this.db.transaction(['syncQueue'], 'readwrite')
      const store = transaction.objectStore('syncQueue')
      const index = store.index('status')
      const request = index.getAll(IDBKeyRange.only('synced'))
      
      return new Promise((resolve, reject) => {
        request.onsuccess = () => {
          const syncedItems = request.result
          syncedItems.forEach(item => {
            store.delete(item.id)
          })
          resolve(syncedItems.length)
        }
        request.onerror = () => reject(request.error)
      })
    } else {
      const queue = JSON.parse(this.storage.getItem('syncQueue') || '[]')
      const remaining = queue.filter(item => item.status !== 'synced')
      this.storage.setItem('syncQueue', JSON.stringify(remaining))
      return Promise.resolve(queue.length - remaining.length)
    }
  }

  // 数据导出/导入
  async exportData(userId) {
    const data = {
      todos: await this.getAllItems('todos', userId),
      sharedLists: await this.getAllItems('sharedLists', userId),
      comments: await this.getAllItems('comments'),
      exportedAt: new Date().toISOString()
    }
    return data
  }

  async importData(data) {
    const results = {
      success: [],
      errors: []
    }
    
    // 导入待办事项
    for (const todo of data.todos || []) {
      try {
        await this.addItem('todos', todo)
        results.success.push(`Todo ${todo.id}`)
      } catch (error) {
        results.errors.push(`Todo ${todo.id}: ${error.message}`)
      }
    }
    
    // 导入共享清单
    for (const list of data.sharedLists || []) {
      try {
        await this.addItem('sharedLists', list)
        results.success.push(`SharedList ${list.id}`)
      } catch (error) {
        results.errors.push(`SharedList ${list.id}: ${error.message}`)
      }
    }
    
    return results
  }
}

// 创建单例实例
export const localStorageService = new LocalStorageService()

// Vue composable for easier usage
export function useLocalStorage() {
  const isOnline = ref(navigator.onLine)
  const isSyncing = ref(false)
  
  // 监听网络状态变化
  window.addEventListener('online', () => {
    isOnline.value = true
  })
  
  window.addEventListener('offline', () => {
    isOnline.value = false
  })
  
  return {
    localStorageService,
    isOnline,
    isSyncing,
    init: () => localStorageService.init()
  }
}