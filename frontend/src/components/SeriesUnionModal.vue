<template>
  <div v-if="visible" class="overlay">
    <div class="modal">
      <h3>Select Items</h3>

      <div v-if="loading">Loading...</div>

      <div v-else>
        <div v-for="item in items" :key="item.key">
          <label>
            <input
              type="checkbox"
              :value="item.key"
              v-model="selected"
            />
            {{ item.name }}
          </label>
        </div>
      </div>

      <div class="modal-actions">
        <button class="ctrl-btn material-symbols-outlined" @click="props.unite(selected)">save</button>
        <button class="ctrl-btn material-symbols-outlined" @click="props.close()">cancel</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Series } from '@/main.ts'


const props = defineProps<{
  items: Series[]
  seriesID?: string
  visible: boolean
  unite: (selected: string[]) => void
  close: () => void
}>()

const selected = ref<string[]>([])
const loading = ref(false)
</script>

<style scoped>
.modal {
  background: var(--backgroundWhite);
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
}

.modal-actions {
  margin-top: 1rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.ctrl-btn {
  padding: 0px 8px;
  margin: 10px 2px;
}
</style>
