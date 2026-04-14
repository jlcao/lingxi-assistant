<template>
  <div class="layout-container">
    <Splitter>
      <template #left>
        <HistoryChat />
      </template>
      <template #center>
        <ChatCore />
      </template>
      <template #right>
        <SkillWorkspace />
      </template>
    </Splitter>
  </div>
</template>

<script setup lang="ts">
import Splitter from './Splitter.vue'
import HistoryChat from './HistoryChat.vue'
import ChatCore from './ChatCore.vue'
import SkillWorkspace from './SkillWorkspace.vue'
</script>

<style scoped lang="scss">
.layout-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}
</style>
