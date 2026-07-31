<template>
  <div ref="root" class="lazy-cover">
    <img
      v-if="loaded && src"
      :src="src"
      class="cover"
      decoding="async"
      fetchpriority="low"
      alt=""
      @load="onDone"
      @error="onDone"
    />
    <div v-else class="cover placeholder" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { acquireThumb, releaseThumb } from '@/utils/thumbQueue'

const props = defineProps<{ src?: string | null }>()

const root = ref<HTMLElement>()
const loaded = ref(false)
let io: IntersectionObserver | null = null
let pending = false
let slotHeld = false
let alive = true

const onDone = () => {
  if (slotHeld) {
    releaseThumb()
    slotHeld = false
  }
}

const teardown = () => {
  alive = false
  io?.disconnect()
  io = null
  pending = false
  if (slotHeld) {
    releaseThumb()
    slotHeld = false
  }
  loaded.value = false
}

const startLoad = async () => {
  if (pending || loaded.value || !props.src || !alive) return
  pending = true
  await acquireThumb()
  pending = false
  if (!alive || !props.src || !root.value) {
    releaseThumb()
    return
  }
  slotHeld = true
  loaded.value = true
}

const observe = () => {
  alive = true
  io?.disconnect()
  io = null
  pending = false
  if (slotHeld) {
    releaseThumb()
    slotHeld = false
  }
  loaded.value = false
  if (!props.src || !root.value) return
  io = new IntersectionObserver(
    ([entry]) => {
      if (!entry?.isIntersecting) return
      io?.disconnect()
      io = null
      void startLoad()
    },
    { rootMargin: '80px' },
  )
  io.observe(root.value)
}

onMounted(observe)
onUnmounted(teardown)
watch(() => props.src, observe)
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
