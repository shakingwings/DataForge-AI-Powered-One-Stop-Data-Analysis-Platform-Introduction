<template>
  <el-card shadow="hover" class="upload-card" body-style="padding: 12px">
    <template #header>
      <div class="card-header">
        <span>数据上传</span>
        <el-button v-if="store.hasData" type="danger" size="small" text @click="handleClear">
          清除
        </el-button>
      </div>
    </template>
    <el-upload
      drag
      :auto-upload="false"
      :on-change="handleFile"
      :show-file-list="false"
      accept=".csv,.xlsx,.xls,.txt"
      v-if="!store.hasData"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
      <template #tip>
        <div class="el-upload__tip">支持 CSV、Excel、TXT 格式</div>
      </template>
    </el-upload>
    <div v-else class="data-summary">
      <el-descriptions :column="1" size="small" border>
        <el-descriptions-item label="文件">{{ store.dataInfo.filename }}</el-descriptions-item>
        <el-descriptions-item label="行数">{{ store.dataInfo.rows }}</el-descriptions-item>
        <el-descriptions-item label="列数">{{ store.dataInfo.columns }}</el-descriptions-item>
      </el-descriptions>
    </div>
  </el-card>
</template>

<script setup>
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../stores/app'
import { uploadData, clearData, autoCharts } from '../api'

const store = useAppStore()

async function handleFile(file) {
  store.loading = true
  try {
    const { data } = await uploadData(file.raw)
    store.dataInfo = data
    store.previewData = data.preview
    ElMessage.success(`上传成功：${data.rows} 行 x ${data.columns} 列`)
    try {
      const { data: chartData } = await autoCharts()
      if (chartData.charts && chartData.charts.length > 0) {
        store.setCharts(chartData.charts)
        store.activeTab = 'charts'
      }
    } catch (_) { /* auto charts optional */ }
  } catch (e) {
    ElMessage.error('上传失败：' + (e.response?.data?.detail || e.message))
  } finally {
    store.loading = false
  }
}

async function handleClear() {
  await clearData()
  store.reset()
  ElMessage.success('数据已清除')
}
</script>

<style scoped>
.upload-card { flex-shrink: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.data-summary { font-size: 13px; }
</style>
