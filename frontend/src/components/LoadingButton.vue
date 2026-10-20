
<template>
  <button :disabled="loading || resetting" class="material-symbols-outlined" :title="title" @click="run">
    <span :class="{ 'custom-throbber-animation': loading }"  @animationiteration="onAnimationIteration">{{ icon }}</span>
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { notify } from '@kyvg/vue3-notification'

const props = withDefaults(defineProps<{
  icon: string
  title?: string
  action: () => Promise<unknown>
  timeout?: number
}>(), { timeout: 3000 })

const icon = ref(props.icon)
const loading = ref(false)
const finished = ref(false)
const resetting = ref(false)

async function onAnimationIteration() {
  if (!finished.value) return
  finished.value = false
  resetting.value = true
  loading.value = false

  await new Promise(resolve => setTimeout(resolve, props.timeout))
  icon.value = props.icon
  resetting.value = false
}

async function run() {
  if (loading.value) return
  loading.value = true

  try {
    await props.action()
    icon.value = 'check'
  } catch (error: any) {
    icon.value = 'error'
    notify({
      title: 'Error',
      text: error?.response?.data?.detail ?? error?.message ?? 'Something went wrong',
      type: 'error'
    })
  } finally {
    finished.value = true
  }
}
</script>



<style scoped>
/* Define the animation for the text content */
.custom-throbber-animation {
    display: inline-block;
    animation: customSpin 2s infinite ease-in-out;
    font-size: 1em;
}

@keyframes customSpin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(2160deg); }
}
</style>