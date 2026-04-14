<template>
  <div class="skill-workspace">
    <FileWorkspace />
  </div>
</template>

<script setup lang="ts">
import FileWorkspace from './workspace/FileWorkspace.vue'
</script>

<style scoped lang="scss">
.skill-workspace {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  border-left: 1px solid #e8e8e8;
}
</style>
