<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <h1>DataForge-AI-Powered-One-Stop-Data-Analysis-Platform</h1>
      </div>
      <div class="header-right">
        <el-tag :type="store.config.llm_provider === 'openai' ? 'primary' : 'success'" size="small">
          {{ store.config.llm_provider === 'openai' ? '在线API' : 'Ollama本地' }}
        </el-tag>
        <el-button :icon="Setting" circle @click="showSettings = true" />
      </div>
    </el-header>
    <el-main class="app-main">
      <el-row :gutter="16" class="full-height">
        <el-col :span="8" class="full-height">
          <div class="left-panel">
            <DataUpload />
            <ChatPanel />
          </div>
        </el-col>
        <el-col :span="16" class="full-height">
          <div class="right-panel">
            <el-tabs v-model="store.activeTab" class="main-tabs">
              <el-tab-pane label="数据预览" name="preview">
                <DataPreview />
              </el-tab-pane>
              <el-tab-pane label="数据清洗" name="cleaning">
                <DataCleaning />
              </el-tab-pane>
              <el-tab-pane label="可视化图表" name="charts">
                <ChartView v-if="store.activeTab === 'charts'" />
              </el-tab-pane>
              <el-tab-pane label="分析结果" name="analysis">
                <AnalysisResult />
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-col>
      </el-row>
    </el-main>
    <SettingsPanel v-model="showSettings" />
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Setting } from '@element-plus/icons-vue'
import { useAppStore } from './stores/app'
import { getConfig } from './api'
import ChatPanel from './components/ChatPanel.vue'
import DataUpload from './components/DataUpload.vue'
import ChartView from './components/ChartView.vue'
import DataPreview from './components/DataPreview.vue'
import AnalysisResult from './components/AnalysisResult.vue'
import DataCleaning from './components/DataCleaning.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const store = useAppStore()
const showSettings = ref(false)

onMounted(async () => {
  try {
    const { data } = await getConfig()
    store.config = { ...store.config, ...data }
  } catch (e) { /* ignore */ }
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }
.app-container { height: 100vh; background: #f0f2f5; }
.app-header {
  display: flex; align-items: center; justify-content: space-between;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff; padding: 0 24px; height: 56px;
}
.app-header h1 { font-size: 20px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 12px; }
.app-main { padding: 16px; height: calc(100vh - 56px); overflow: hidden; }
.full-height { height: 100%; }
.left-panel {
  height: 100%; display: flex; flex-direction: column; gap: 12px;
}
.right-panel {
  height: 100%; background: #fff; border-radius: 12px;
  padding: 16px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.main-tabs { height: 100%; }
.main-tabs .el-tabs__content { height: calc(100% - 40px); overflow: auto; }
.main-tabs .el-tab-pane { height: 100%; }
</style>
