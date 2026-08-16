<script setup lang="ts">
defineProps<{
  role?: 'user' | 'admin' | string
}>()
</script>

<template>
  <span 
    v-if="role === 'admin'" 
    class="admin-badge" 
    title="Администратор"
  >
    👑
  </span>
</template>

<style scoped>
.admin-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 6px;
  font-size: 0.85em;
  cursor: help;
  user-select: none;
  /* Небольшая анимация или подсвечивание при желании */
  transition: transform 0.2s ease;
}

.admin-badge:hover {
  transform: scale(1.15);
}
</style>