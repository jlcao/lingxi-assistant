<template>
  <div class="home">
    <ChatCore />
  </div>
</template>

<script setup lang="ts">
import ChatCore from '../components/ChatCore.vue'
</script>

<style scoped>
.home {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
