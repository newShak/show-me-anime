<template>
  <div ref="root" class="lazy-cover">
    <img
      v-if="shown && src"
      :src="src"
      class="cover"
      decoding="async"
      fetchpriority="low"
      alt=""
    />
    <div v-else class="cover placeholder" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps<{ src?: string | null }>()

const root = ref<HTMLElement>()
const shown = ref(false)
let io: IntersectionObserver | null = null

const resetObserve = () => {
  io?.disconnect()
  shown.value = false
  if (!props.src || !root.value) return
  io = new IntersectionObserver(
    ([entry]) => {
      if (!entry?.isIntersecting) return
      shown.value = true
      io?.disconnect()
    },
    { rootMargin: '160px' },
  )
  io.observe(root.value)
}

onMounted(resetObserve)
onUnmounted(() => io?.disconnect())
watch(() => props.src, () => resetObserve())
</script>

<style scoped>
.lazy-cover {
  display: block;
  width: 100%;
}

.cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  display: block;
}

.placeholder {
  background: var(--app-cover-bg);
}
</style>
