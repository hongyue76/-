<template>
  <div class="todos">
    <todo-list />
  </div>
</template>

<script setup>
import TodoList from '../components/TodoList.vue'
</script>

<style scoped>
.todos {
  height: 100%;
}
</style>