# 离线支持功能扩展文档

## 功能概述

本次扩展为待办事项应用增加了完整的离线支持功能，使用户在网络不稳定或断网情况下仍能正常使用应用的核心功能。

## 核心功能特性

### 1. 本地数据存储
- **双存储引擎**：优先使用 IndexedDB，降级使用 localStorage
- **数据持久化**：所有用户数据本地备份
- **版本控制**：支持数据版本管理和迁移

### 2. 智能同步机制
- **增量同步**：只同步变更的数据
- **冲突解决**：基于时间戳的智能冲突处理
- **断点续传**：网络恢复后自动继续同步
- **重试机制**：失败操作自动重试（最多3次）

### 3. 网络状态监测
- **实时检测**：持续监控网络连接状态
- **质量评估**：网络速度和稳定性评分
- **服务器连通性**：定期检查服务器可达性
- **状态变化通知**：网络状态变化时及时通知

### 4. 用户体验优化
- **无缝切换**：在线/离线模式自动切换
- **状态指示器**：清晰的网络状态可视化
- **操作反馈**：离线操作的明确提示
- **数据一致性**：保证本地和服务器数据最终一致性

## 技术实现

### 本地存储服务 (localStorageService.js)

#### 核心功能
```javascript
class LocalStorageService {
  // 初始化数据库
  async init()
  
  // 数据操作
  async addItem(storeName, item)
  async updateItem(storeName, item)
  async deleteItem(storeName, id)
  async getAllItems(storeName, userId)
  
  // 同步队列管理
  async addToSyncQueue(operation)
  async getSyncQueue()
  async updateSyncQueueItem(id, updates)
}
```

#### 存储结构
- **todos**：待办事项数据
- **sharedLists**：共享清单数据
- **comments**：评论数据
- **syncQueue**：待同步操作队列

### 数据同步服务 (syncService.js)

#### 同步流程
1. **上传本地变更**：将本地修改推送到服务器
2. **下载服务器更新**：获取服务器最新数据
3. **冲突解决**：处理数据冲突
4. **清理同步队列**：移除已成功的同步项

#### 冲突解决策略
- **时间戳比较**：本地更新时间 vs 服务器更新时间
- **用户优先**：本地修改优先保留
- **自动合并**：尽可能合并双方数据

### 网络监控服务 (networkMonitor.js)

#### 监控指标
- **基本连通性**：navigator.onLine 状态
- **服务器可达性**：定期ping健康检查端点
- **网络质量**：连接类型、带宽、延迟
- **数据节省模式**：浏览器数据节省状态

#### 质量评分算法
```
基础分：100分
连接类型扣分：
- slow-2g: -60分
- 2g: -40分
- 3g: -20分
- 4g: 0分

延迟扣分：
- RTT > 200ms: -20分
- RTT > 100ms: -10分

带宽扣分：
- 下行 < 1Mbps: -20分
- 下行 < 5Mbps: -10分
```

## 使用场景

### 典型使用流程

1. **正常在线使用**
   - 用户正常使用应用
   - 数据实时同步到服务器
   - 本地同时保存备份

2. **网络中断**
   - 应用自动检测到断网
   - 切换到离线模式
   - 用户操作保存到本地
   - 状态指示器显示离线状态

3. **离线操作**
   - 创建、编辑、删除待办事项
   - 所有操作本地保存
   - 明确提示用户数据将稍后同步

4. **网络恢复**
   - 自动检测网络恢复
   - 启动同步流程
   - 上传本地变更
   - 下载服务器更新
   - 解决可能的冲突

## API 接口

### 网络状态 API
```javascript
// 获取网络状态
const { isOnline, networkStatus } = useNetwork()

// 获取网络质量评分 (0-100)
const qualityScore = getNetworkQualityScore()

// 添加网络状态监听器
addNetworkListener((event) => {
  console.log('网络状态变化:', event)
})
```

### 同步服务 API
```javascript
// 启动同步服务
const { startSync, stopSync } = useSync()

// 强制同步
await forceSync()

// 获取同步状态
const status = await getSyncStatus()
```

### 本地存储 API
```javascript
// 初始化本地存储
const { init } = useLocalStorage()

// 数据操作
await localStorageService.addItem('todos', todoData)
await localStorageService.updateItem('todos', updatedTodo)
await localStorageService.deleteItem('todos', todoId)
```

## 状态管理集成

### 待办事项 Store 增强
```javascript
const useTodosStore = defineStore('todos', () => {
  // 自动根据网络状态选择数据源
  const fetchTodos = async () => {
    if (isOnline.value) {
      // 从服务器获取并更新本地存储
    } else {
      // 从本地存储获取
    }
  }
  
  // 离线友好的操作
  const addTodo = async (todoData) => {
    if (isOnline.value) {
      // 直接创建到服务器
    } else {
      // 保存到本地，标记待同步
    }
  }
})
```

## UI 组件

### 离线状态指示器 (OfflineIndicator.vue)

#### 功能特性
- **实时状态显示**：网络连接状态、服务器可达性
- **质量评分展示**：网络质量百分比显示
- **详细信息面板**：连接类型、延迟、带宽等详细信息
- **重试功能**：手动触发同步
- **离线提示横幅**：网络断开时的友好提醒

#### 显示状态
- 🟢 **绿色**：网络良好，服务器连接正常
- 🟡 **黄色**：网络较差或服务器连接异常
- 🔴 **红色**：完全离线

## 配置选项

### 同步配置
```javascript
const syncConfig = {
  syncIntervalMs: 30000,    // 自动同步间隔 (30秒)
  maxRetries: 3,            // 最大重试次数
  retryDelay: 1000,         // 基础重试延迟 (1秒)
  pingIntervalMs: 30000     // 服务器连通性检查间隔
}
```

### 存储配置
```javascript
const storageConfig = {
  dbName: 'todoAppDB',      // IndexedDB 数据库名
  version: 1,               // 数据库版本
  fallbackToLocalStorage: true  // 是否降级到 localStorage
}
```

## 性能优化

### 数据优化
- **增量更新**：只传输变更部分
- **数据压缩**：传输前压缩大型数据
- **批量操作**：合并多个操作减少请求次数

### 存储优化
- **数据清理**：定期清理已同步的历史记录
- **空间管理**：监控存储空间使用情况
- **索引优化**：合理使用数据库索引提高查询效率

## 错误处理

### 网络错误
- **超时处理**：设置合理的请求超时时间
- **重试机制**：指数退避重试策略
- **降级方案**：网络异常时的功能降级

### 数据错误
- **校验机制**：数据完整性和有效性检查
- **恢复策略**：损坏数据的修复和恢复
- **用户提示**：清晰的错误信息和解决方案

## 测试建议

### 网络模拟测试
```javascript
// Chrome DevTools 网络节流预设
// Fast 3G, Slow 3G, Offline 等场景测试

// 手动测试场景
// 1. 正常使用 → 断网 → 离线操作 → 恢复网络 → 自动同步
// 2. 多设备同时操作产生的冲突处理
// 3. 长时间离线后的大量数据同步
```

### 性能测试
- **存储容量**：大量数据下的性能表现
- **同步效率**：大数据量同步的时间消耗
- **内存使用**：长时间运行的内存泄漏检查

## 部署注意事项

### 生产环境配置
1. **健康检查端点**：确保 `/health` 端点可用
2. **CORS 配置**：正确配置跨域资源共享
3. **HTTPS**：生产环境必须使用 HTTPS
4. **缓存策略**：合理配置静态资源缓存

### 监控指标
- 网络连接成功率
- 同步操作成功率
- 用户离线时长分布
- 冲突发生频率

## 后续扩展方向

### 即将实现的功能
- [ ] 智能预加载：预测用户行为提前加载数据
- [ ] 增量备份：重要数据的云端备份
- [ ] 多设备同步：跨设备的状态同步
- [ ] 离线搜索：本地全文搜索功能

### 性能改进
- [ ] Service Worker 支持
- [ ] 数据库查询优化
- [ ] 更智能的同步时机选择
- [ ] 压缩算法优化

这个离线支持系统为应用提供了企业级的可靠性保障，确保用户在任何网络环境下都能获得良好的使用体验。