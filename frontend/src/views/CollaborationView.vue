<template>
  <div class="collaboration-dashboard">
    <el-row :gutter="20">
      <!-- 左侧导航 -->
      <el-col :span="6">
        <el-card class="navigation-card">
          <template #header>
            <div class="card-header">
              <h3>协作中心</h3>
            </div>
          </template>
          <el-menu
            :default-active="activeMenu"
            class="navigation-menu"
            @select="handleMenuSelect"
          >
            <el-menu-item index="shared-lists">
              <el-icon><List /></el-icon>
              <span>共享清单</span>
            </el-menu-item>
            <el-menu-item index="team-tasks">
              <el-icon><Checked /></el-icon>
              <span>团队任务</span>
            </el-menu-item>
            <el-menu-item index="activity">
              <el-icon><Bell /></el-icon>
              <span>活动动态</span>
            </el-menu-item>
            <el-menu-item index="analytics">
              <el-icon><DataAnalysis /></el-icon>
              <span>数据分析</span>
            </el-menu-item>
          </el-menu>
        </el-card>
      </el-col>

      <!-- 右侧内容区域 -->
      <el-col :span="18">
        <el-card class="content-card">
          <template #header>
            <div class="card-header">
              <h2>{{ currentTitle }}</h2>
            </div>
          </template>
          
          <!-- 共享清单管理 -->
          <div v-if="activeMenu === 'shared-lists'">
            <shared-lists-manager />
          </div>

          <!-- 团队任务视图 -->
          <div v-else-if="activeMenu === 'team-tasks'">
            <div class="feature-placeholder">
              <el-empty description="团队任务功能正在开发中...">
                <el-button type="primary">敬请期待</el-button>
              </el-empty>
            </div>
          </div>

          <!-- 活动动态 -->
          <div v-else-if="activeMenu === 'activity'">
            <div class="feature-placeholder">
              <el-empty description="活动动态功能正在开发中...">
                <el-button type="primary">敬请期待</el-button>
              </el-empty>
            </div>
          </div>

          <!-- 数据分析 -->
          <div v-else-if="activeMenu === 'analytics'">
            <div class="feature-placeholder">
              <el-empty description="数据分析功能正在开发中...">
                <el-button type="primary">敬请期待</el-button>
              </el-empty>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SharedListsManager from '../components/SharedListsManager.vue'
import { List, Checked, Bell, DataAnalysis } from '@element-plus/icons-vue'

const activeMenu = ref('shared-lists')

const menuTitles = {
  'shared-lists': '共享清单管理',
  'team-tasks': '团队任务分配',
  'activity': '团队活动动态',
  'analytics': '协作数据分析'
}

const currentTitle = computed(() => {
  return menuTitles[activeMenu.value] || '协作中心'
})

const handleMenuSelect = (index) => {
  activeMenu.value = index
}
</script>

<style scoped>
.collaboration-dashboard {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.navigation-card, .content-card {
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
}

.navigation-card :deep(.el-card__body) {
  flex: 1;
  padding: 0;
}

.content-card :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-header h2, .card-header h3 {
  margin: 0;
  color: #303133;
}

.navigation-menu {
  border: none;
}

.navigation-menu .el-menu-item {
  height: 50px;
  line-height: 50px;
}

.feature-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>