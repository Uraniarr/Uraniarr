<template>
  <div class="series-list">
    <div
      v-for="group in seriesGroups"
      :key="group.series.key"
      class="series-group"
      :style="{ maxHeight: collapseMap[group.series.key] ? '100%' : '40px' }"
    >
      <div style="display: flex;">
        <button title="Collapse series" class="collapse-btn material-symbols-outlined" @click="collapseMap[group.series.key] = !collapseMap[group.series.key]">
          {{ collapseMap[group.series.key] ? 'keyboard_arrow_up' : 'keyboard_arrow_down' }}
        </button>
        <div class="series-name">
          <div class="name-container">
            <span v-if="!showEditSeriesMap[group.series.key]">
              {{ group.series.name }}
            </span>
            <input v-else type="text" v-model="newNameSeries"
              @keyup.enter="props.editSeries(group.series.key, { name: newNameSeries }); showEditSeriesMap[group.series.key] = false"
              @keyup.esc="newNameSeries = ''; showEditSeriesMap[group.series.key] = false"/>
            <button v-if="!showEditSeriesMap[group.series.key]" class="edit-btn material-symbols-outlined"
              @click="showEditSeriesMap[group.series.key] = true; newNameSeries = group.series.name;" title="Edit the series name"
            >edit</button>
          </div>
          <span class="series-id">({{ group.series.key }})</span>
        </div>
        <button v-if="!showCleanup[group.series.key]" title="Attempt to clean Book titles of remnants from series" class="ctrl-btn material-symbols-outlined" @click="showCleanup[group.series.key] = true">cleaning_services</button>
        <div v-else style="display: flex;">
          <input class="series-clean" @keyup.enter="props.cleanupSeries(group.series.key, ($event.target as HTMLInputElement).value)" type="text" placeholder="alternative Series title" :key="group.series.key"/>
          <button class="ctrl-btn material-symbols-outlined" @click="showCleanup[group.series.key] = false">arrow_right</button>
        </div>
        <button title="Join Series" class="ctrl-btn material-symbols-outlined" @click="openSelector(group.series.key)">join</button>
        <LoadingButton title="Complete series (use if missing)" class="ctrl-btn" icon="matter" :action="() => props.completeSeries(group.series.key)"/>
        <LoadingButton title="Download every book of series" class="ctrl-btn" icon="download" :action="() => props.downloadSeries(group.series.key)"/>
        <button title="Delete entire series from database" class="ctrl-btn material-symbols-outlined" @click="props.deleteSeries(group.series.key)">delete</button>
      </div>
      <BookList
        :downloadBook="props.downloadBook"
        :deleteBook="props.deleteBook"
        :editBook="props.editBook"
        :searchBook="props.searchBook"
        :dndDownload="props.dndDownload"
        :showBox="showBox" :books="group.books" :seriesGroups="[]"
        :audio="audio"/>
    </div>
  </div>

  <SeriesUnionSelector
    :items="items"
    :seriesID="seriesID"
    :visible="showSelector"
    :close="closeSelector"
    :unite="uniteSeries"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SeriesUnionSelector from '@/components/SeriesUnionModal.vue'
import BookList from './BookList.vue'
import LoadingButton from './LoadingButton.vue'
import type { Book, Series } from '@/main.ts'
import type { DownloadType } from '@/utils.ts'


const props = defineProps<{
  showBox: boolean
  seriesGroups: Array<{ series: Series; books: Book[] }>
  audio: boolean
  downloadBook: (keys: string[]) => Promise<void>
  dndDownload?: (key: string, file: File, type: DownloadType) => Promise<void>
  searchBook: (key: string) => void
  completeSeries: (key: string) => Promise<void>
  downloadSeries: (key: string) => Promise<void>
  deleteSeries: (key: string) => void
  deleteBook: (keys: string[]) => void
  uniteSeries: (keys: { series_id: string; series_ids: string[] }) => void
  editSeries: (key: string, payload: {}) => void
  editBook: (book: Book) => void
  cleanupSeries: (key: string, name: string) => void
}>()

const collapseMap = ref<Record<string, boolean>>({})
const showEditSeriesMap = ref<Record<string, boolean>>({})
const showCleanup = ref<Record<string, boolean | undefined>>({})
const showBox = ref(false)

const seriesID = ref()
const showSelector = ref(false)
const items = ref<Series[]>([])
const newNameSeries = ref("")

function uniteSeries(selected: string[]) {
  props.uniteSeries({ series_id: seriesID.value, series_ids: selected })
  closeSelector()
}

function closeSelector() {
  seriesID.value = null
  showSelector.value = false
}

function openSelector(id: string) {
  seriesID.value = id
  showSelector.value = true

  const filteredItems = props.seriesGroups.reduce((acc, curr) => {
    if (curr.series.key !== id) {
      acc.push(curr.series)
    }
    return acc
  }, [] as Series[])
  items.value = filteredItems
}

</script>

<style scoped>
.series-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  box-sizing: border-box;
}

.series-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 10px;
  padding-bottom: 20px;
  border: 1px solid var(--borderColor);
  background-color: var(--offWhite);
  border-radius: 8px;
  overflow: hidden;
}

.ctrl-btn{
  padding: 0px 8px;
  margin: 10px 2px;
}

.series-clean{
  margin: 10px 2px;
}

.series-name {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 1.2rem;
  font-weight: 600;
  margin: 10px 10px;
  flex-grow: 1;
}

.name-container:hover .edit-btn{
  display: block;
}

.edit-btn{
  font-size: 12pt;
  margin: 0 6px;
  display: none;
}

.name-container{
  display: flex;
  align-items: center
}

.series-id{
  font-size: 0.85rem;
  color: gray;
}

.group{
  border:none;
  background-color: transparent;
  padding: 0;
  margin: 0;
}

.collapse-btn{
  color: var(--lightGray);
  background-color: transparent;
  margin: 10px 0;
}
</style>
