<template>
  <div v-if="visible" class="overlay">
    <div class="modal">
      <h2>Configure Send to Kindle</h2>

      <form @submit.prevent="handleSubmit">
        <label>
          Email Address:
          <input v-model="form.email_address" type="email" required />
        </label>

        <label>
          App Password:
          <input v-model="form.password" type="password" required />
        </label>

        <label>
          SMTP Server:
          <input v-model="form.smtp_server" placeholder="smtp.gmail.com" required />
        </label>

        <label>
          SMTP Port:
          <input v-model.number="form.smtp_port" type="number" required />
        </label>

        <label>
          Kindle Emails (comma-separated):
          <input v-model="form.kindle_emails" placeholder="kindle1@kindle.com, kindle2@kindle.com" required />
        </label>

        <div class="actions">
          <button class="btns material-symbols-outlined" type="submit">save</button>
          <button class="btns material-symbols-outlined" type="button" @click="props.close()">close</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { KindleConfig } from "@/main";
import { reactive, watch } from "vue"

const props = defineProps<{
  visible: boolean
  cfg: KindleConfig
  save: (cfg: KindleConfig) => void | Promise<void>
  close: () => void
}>()

const form = reactive<KindleConfig>({ ...props.cfg })

watch(
  () => [props.cfg, props.visible],
  () => Object.assign(form, props.cfg),
  { immediate: true }
)

async function handleSubmit() {
  await props.save({ ...form })
}
</script>

<style scoped>
.overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal {
  background-color: var(--backgroundWhite);
  padding: 20px;
  width: 500px;
  border-radius: 8px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h2 {
  margin-top: 0;
}

label {
  display: block;
  font-weight: 500;
  margin-bottom: 12px;
}

input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.btns {
  padding: 8px;
  cursor: pointer;
}
</style>