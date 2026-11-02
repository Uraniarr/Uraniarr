
<template>
  <div class="downloader-list">
    <div class="cards">
      <div v-for="(downloader, idx) in downloaders" :key="downloader.name" class="card downloader-card" draggable="true"
        :class="{ dragging: draggedIndex === idx }" @dragstart="draggedIndex = idx" @dragover.prevent @drop.prevent="onDrop(idx)"
        @dragend="draggedIndex = null"
      >
        <div>
          <div class="title">{{ downloader.name }}</div>
          <div class="subtitle">{{ downloader.type }}</div>
        </div>
        <button type="button" class="edit-btn material-symbols-outlined" @click="props.editDownloader(idx)">
          edit
        </button>
      </div>

      <div class="card add-card" @click="props.editDownloader(downloaders.length)">
        <span class="plus material-symbols-outlined">add</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { Downloader } from "@/main.ts";

const props = defineProps<{
  downloaders: Downloader[];
  editDownloader: (idx: number) => void;
  applyDeepChange: (key: string, downloaders: Downloader[]) => void;
}>();

const draggedIndex = ref<number | null>(null);

function onDrop(targetIndex: number) {
  const fromIndex = draggedIndex.value;
  draggedIndex.value = null;

  if (fromIndex === null || fromIndex === targetIndex) return;

  const reordered = [...props.downloaders];
  const [item] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, item);
  console.log(reordered)
  props.applyDeepChange("downloaders", reordered)
}
</script>

<style scoped>
.downloader-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.cards {
  display: flex;
  gap: 1.25rem;
  margin-top: 1rem;
}

.card {
  background: var(--backgroundWhite);
  border-radius: 6px;
  max-width: 260px;
  min-width: 50px;
  height: 50px;
  padding: 10px;
  display: flex;
  gap: 10px;
}

.downloader-card{
  cursor: grab;
}
.downloader-card:active {
  cursor: grabbing;
}
.downloader-card.dragging {
  opacity: 0.4;
}

.downloader-card .title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: auto 0;
}

.downloader-card .subtitle {
  opacity: 0.7;
  font-size: 0.9rem;
  margin-top: 0.25rem;
}



/* Add card */
.add-card {
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  width: 50px;
  height: 50px;
}

.add-card:hover .plus {
  color: white;
}

.plus {
  font-size: 36px;
  color: #bbb;
}
</style>
