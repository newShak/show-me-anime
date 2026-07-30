<template>
  <AppNav v-if="showNav" />
  <router-view />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppNav from '@/components/AppNav.vue'

const route = useRoute()
const showNav = computed(() => !route.path.startsWith('/reader'))
</script>

<style scoped></style>
