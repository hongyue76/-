<template>
  <el-menu
    mode="horizontal"
    :default-active="activeIndex"
    @select="handleSelect"
    background-color="#545c64"
    text-color="#fff"
    active-text-color="#ffd04b"
  >
    <el-menu-item index="/">首页</el-menu-item>
    
    <template v-if="!authStore.isAuthenticated">
      <el-menu-item index="/login">登录</el-menu-item>
      <el-menu-item index="/register">注册</el-menu-item>
    </template>
    
    <template v-else>
      <el-menu-item index="/todos">我的待办</el-menu-item>
      <el-menu-item index="/collaboration">协作中心</el-menu-item>
      <el-sub-menu index="user">
        <template #title>{{ authStore.user?.username }}</template>
        <el-menu-item @click="handleLogout">退出登录</el-menu-item>
      </el-sub-menu>
    </template>
  </el-menu>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const activeIndex = computed(() => route.path)

const handleSelect = (key) => {
  router.push(key)
}

const handleLogout = async () => {
  authStore.logout()
  ElMessage.success('已退出登录')
  router.push('/')
}
</script>