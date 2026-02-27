<template>
  <div class="home">
    <el-row justify="center">
      <el-col :span="12">
        <el-card class="welcome-card">
          <template #header>
            <div class="card-header">
              <h1>欢迎使用待办事项应用</h1>
            </div>
          </template>
          <div class="content">
            <p>这是一个功能强大的多用户同步待办事项管理应用</p>
            <div class="features">
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-card shadow="hover">
                    <h3>📋 待办管理</h3>
                    <p>轻松创建、编辑和管理您的待办事项</p>
                  </el-card>
                </el-col>
                <el-col :span="8">
                  <el-card shadow="hover">
                    <h3>🔄 实时同步</h3>
                    <p>多设备间实时数据同步，永不丢失</p>
                  </el-card>
                </el-col>
                <el-col :span="8">
                  <el-card shadow="hover">
                    <h3>👥 协作共享</h3>
                    <p>与团队成员共享清单，协同工作</p>
                  </el-card>
                </el-col>
              </el-row>
            </div>
            <div class="actions" v-if="!authStore.isAuthenticated">
              <el-button type="primary" size="large" @click="$router.push('/register')">
                立即注册
              </el-button>
              <el-button size="large" @click="$router.push('/login')">
                登录账户
              </el-button>
            </div>
            <div class="actions" v-else>
              <el-button type="primary" size="large" @click="$router.push('/todos')">
                查看我的待办
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
const authStore = useAuthStore()
</script>

<style scoped>
.home {
  padding: 40px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: calc(100vh - 60px);
}

.welcome-card {
  border-radius: 15px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

.card-header h1 {
  text-align: center;
  color: #333;
  margin: 0;
}

.content {
  text-align: center;
}

.content p {
  font-size: 18px;
  color: #666;
  margin-bottom: 30px;
}

.features {
  margin: 30px 0;
}

.features h3 {
  margin: 0 0 10px 0;
  color: #333;
}

.features p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.actions {
  margin-top: 30px;
}

.actions .el-button {
  margin: 0 10px;
}
</style>