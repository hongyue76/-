import { ref, reactive } from 'vue'

class NetworkMonitor {
  constructor() {
    const hasWindow = typeof window !== 'undefined'
    const hasNavigator = hasWindow && typeof navigator !== 'undefined'
    
    this.isOnline = ref(hasNavigator ? navigator.onLine : true)
    this.connection = hasNavigator ? (navigator.connection || navigator.mozConnection || navigator.webkitConnection) : null
    this.networkStatus = reactive({
      online: hasNavigator ? navigator.onLine : true,
      type: this.connection?.effectiveType || 'unknown',
      downlink: this.connection?.downlink || 0,
      rtt: this.connection?.rtt || 0,
      saveData: this.connection?.saveData || false,
      serverReachable: true // 默认假设服务器可达
    })
    
    this.listeners = []
    this.pingInterval = null
    this.pingUrl = '/health' // 健康检查端点
    this.pingIntervalMs = 30000 // 30秒检查一次
    
    this.setupEventListeners()
    this.startPingCheck()
  }

  setupEventListeners() {
    // 网络状态变化事件
    window.addEventListener('online', () => {
      this.handleOnline()
    })
    
    window.addEventListener('offline', () => {
      this.handleOffline()
    })
    
    // 网络连接信息变化
    if (this.connection) {
      this.connection.addEventListener('change', () => {
        this.updateNetworkInfo()
      })
    }
  }

  handleOnline() {
    console.log('网络连接已恢复')
    this.isOnline.value = true
    this.networkStatus.online = true
    this.updateNetworkInfo()
    
    // 通知所有监听器
    this.notifyListeners('online')
    
    // 触发同步
    this.triggerSync()
  }

  handleOffline() {
    console.log('网络连接已断开')
    this.isOnline.value = false
    this.networkStatus.online = false
    
    // 通知所有监听器
    this.notifyListeners('offline')
  }

  updateNetworkInfo() {
    if (this.connection) {
      this.networkStatus.type = this.connection.effectiveType || 'unknown'
      this.networkStatus.downlink = this.connection.downlink || 0
      this.networkStatus.rtt = this.connection.rtt || 0
      this.networkStatus.saveData = this.connection.saveData || false
    }
  }

  startPingCheck() {
    // 定期检查服务器连接状态
    this.pingInterval = setInterval(async () => {
      if (this.isOnline.value) {
        await this.pingServer()
      }
    }, this.pingIntervalMs)
  }

  stopPingCheck() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  async pingServer() {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // 5秒超时
      
      const response = await fetch(this.pingUrl, {
        method: 'GET',
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      // 服务器连接正常
      this.networkStatus.serverReachable = true
      this.notifyListeners('server-online')
      
    } catch (error) {
      console.warn('服务器连接检查失败:', error)
      this.networkStatus.serverReachable = false
      this.notifyListeners('server-offline')
    }
  }

  async checkConnectivity() {
    // 综合网络检测
    const checks = {
      navigatorOnline: navigator.onLine,
      serverReachable: false,
      connectionQuality: this.networkStatus.type
    }
    
    try {
      await this.pingServer()
      checks.serverReachable = this.networkStatus.serverReachable
    } catch (error) {
      checks.serverReachable = false
    }
    
    return checks
  }

  // 添加状态变化监听器
  addListener(callback) {
    this.listeners.push(callback)
  }

  // 移除监听器
  removeListener(callback) {
    const index = this.listeners.indexOf(callback)
    if (index > -1) {
      this.listeners.splice(index, 1)
    }
  }

  // 通知监听器
  notifyListeners(eventType) {
    const eventData = {
      type: eventType,
      timestamp: new Date().toISOString(),
      networkStatus: { ...this.networkStatus }
    }
    
    this.listeners.forEach(callback => {
      try {
        callback(eventData)
      } catch (error) {
        console.error('网络状态监听器执行出错:', error)
      }
    })
  }

  // 触发同步（需要外部传入syncService）
  triggerSync() {
    if (typeof this.syncCallback === 'function') {
      this.syncCallback()
    }
  }

  // 设置同步回调
  setSyncCallback(callback) {
    this.syncCallback = callback
  }

  // 获取网络质量评分 (0-100)
  getNetworkQualityScore() {
    if (!this.isOnline.value) return 0
    
    let score = 100
    
    // 基于连接类型扣分
    switch (this.networkStatus.type) {
      case 'slow-2g':
        score -= 60
        break
      case '2g':
        score -= 40
        break
      case '3g':
        score -= 20
        break
      case '4g':
        // 不扣分
        break
      default:
        score -= 30 // unknown
    }
    
    // 基于延迟扣分
    if (this.networkStatus.rtt > 200) {
      score -= 20
    } else if (this.networkStatus.rtt > 100) {
      score -= 10
    }
    
    // 基于带宽扣分
    if (this.networkStatus.downlink < 1) {
      score -= 20
    } else if (this.networkStatus.downlink < 5) {
      score -= 10
    }
    
    return Math.max(0, Math.min(100, score))
  }

  // 销毁监听器
  destroy() {
    this.stopPingCheck()
    this.listeners = []
  }
}

// 创建单例实例
export const networkMonitor = new NetworkMonitor()

// Vue composable
export function useNetwork() {
  // 添加安全检查
  const safeNetworkMonitor = networkMonitor || {
    isOnline: { value: typeof navigator !== 'undefined' ? navigator.onLine : true },
    networkStatus: {
      online: typeof navigator !== 'undefined' ? navigator.onLine : true,
      type: 'unknown',
      downlink: 0,
      rtt: 0,
      saveData: false,
      serverReachable: true
    },
    checkConnectivity: async () => ({
      navigatorOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
      serverReachable: true,
      connectionQuality: 'unknown'
    }),
    getNetworkQualityScore: () => typeof navigator !== 'undefined' && navigator.onLine ? 80 : 0,
    addListener: () => {},
    removeListener: () => {}
  };
  
  return {
    isOnline: safeNetworkMonitor.isOnline,
    networkStatus: safeNetworkMonitor.networkStatus,
    checkConnectivity: () => safeNetworkMonitor.checkConnectivity(),
    getNetworkQualityScore: () => safeNetworkMonitor.getNetworkQualityScore(),
    addNetworkListener: (callback) => safeNetworkMonitor.addListener(callback),
    removeNetworkListener: (callback) => safeNetworkMonitor.removeListener(callback)
  }
}

// 网络状态指示器组件
export function NetworkStatusIndicator() {
  const { isOnline, networkStatus, getNetworkQualityScore } = useNetwork()
  
  const getStatusColor = () => {
    if (!isOnline.value) return '#f56c6c' // 红色 - 离线
    if (!networkStatus.serverReachable) return '#e6a23c' // 黄色 - 服务器不可达
    const quality = getNetworkQualityScore()
    if (quality < 50) return '#e6a23c' // 黄色 - 网络质量差
    return '#67c23a' // 绿色 - 正常
  }
  
  const getStatusText = () => {
    if (!isOnline.value) return '离线'
    if (!networkStatus.serverReachable) return '服务器连接异常'
    const quality = getNetworkQualityScore()
    if (quality < 30) return '网络较差'
    if (quality < 70) return '网络一般'
    return '网络良好'
  }
  
  return {
    color: getStatusColor(),
    text: getStatusText(),
    quality: getNetworkQualityScore()
  }
}