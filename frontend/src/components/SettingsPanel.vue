<template>
  <el-drawer title="设置" :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" size="400px">
    <el-form label-width="100px" label-position="top">
      <el-divider content-position="left">LLM模型设置</el-divider>

      <el-form-item label="模型提供商">
        <el-radio-group v-model="form.llm_provider">
          <el-radio-button value="openai">在线API</el-radio-button>
          <el-radio-button value="ollama">Ollama本地</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <template v-if="form.llm_provider === 'openai'">
        <el-form-item label="API Key">
          <el-input v-model="form.openai_api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.openai_base_url" placeholder="https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="form.openai_model" placeholder="gpt-4o-mini" />
        </el-form-item>
        <el-alert type="info" :closable="false" show-icon>
          支持所有OpenAI兼容API：DeepSeek、通义千问、智谱等
        </el-alert>
      </template>

      <template v-if="form.llm_provider === 'ollama'">
        <el-form-item label="Ollama地址">
          <el-input v-model="form.ollama_url" placeholder="http://localhost:11434" />
        </el-form-item>
        <el-form-item label="模型名称">
          <el-input v-model="form.ollama_model" placeholder="qwen2.5:7b" />
        </el-form-item>
        <el-alert type="warning" :closable="false" show-icon>
          请确保Ollama服务已启动，且模型已下载：ollama pull qwen2.5:7b
        </el-alert>
      </template>

      <el-form-item style="margin-top: 20px;">
        <el-button type="primary" @click="saveConfig" :loading="saving">保存设置</el-button>
      </el-form-item>
    </el-form>
  </el-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../stores/app'
import { updateConfig } from '../api'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])
const store = useAppStore()
const saving = ref(false)
const form = ref({ ...store.config })

watch(() => props.modelValue, (v) => {
  if (v) form.value = { ...store.config }
})

async function saveConfig() {
  saving.value = true
  try {
    await updateConfig(form.value)
    store.config = { ...form.value }
    ElMessage.success('设置已保存')
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>
