import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  const messages = ref([])
  const dataInfo = ref(null)
  const previewData = ref([])
  const charts = ref([])
  const analysisResult = ref({})
  const loading = ref(false)
  const activeTab = ref('preview')
  const config = ref({
    llm_provider: 'openai',
    openai_api_key: '',
    openai_base_url: 'https://api.openai.com/v1',
    openai_model: 'gpt-4o-mini',
    ollama_model: 'qwen2.5:7b',
    ollama_url: 'http://localhost:11434',
  })

  const hasData = computed(() => !!dataInfo.value)
  const columnNames = computed(() => dataInfo.value?.column_names || [])

  function addMessage(msg) {
    messages.value.push(msg)
  }

  function updateCharts(newCharts) {
    charts.value = [...charts.value, ...newCharts]
  }

  function setCharts(newCharts) {
    charts.value = newCharts
  }

  function removeChart(index) {
    charts.value.splice(index, 1)
  }

  function updateChartAt(index, chartData) {
    charts.value[index] = chartData
  }

  function reset() {
    messages.value = []
    dataInfo.value = null
    previewData.value = []
    charts.value = []
    analysisResult.value = {}
  }

  return {
    messages, dataInfo, previewData, charts, analysisResult,
    loading, config, hasData, columnNames, activeTab,
    addMessage, updateCharts, setCharts, removeChart, updateChartAt, reset,
  }
})
