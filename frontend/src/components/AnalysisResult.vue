<template>
  <div class="analysis-container">
    <div v-if="!store.hasData" class="empty">
      <el-empty description="请先上传数据文件" />
    </div>
    <div v-else>
      <div class="toolbar">
        <el-button size="small" type="primary" @click="runBasicStats">
          <el-icon><DataAnalysis /></el-icon>基础统计
        </el-button>
        <el-button size="small" @click="runCorrelation">
          <el-icon><Connection /></el-icon>相关性分析
        </el-button>
        <el-button size="small" @click="runAnomaly">
          <el-icon><Warning /></el-icon>异常检测
        </el-button>
        <el-button size="small" type="success" @click="exportReport">
          <el-icon><Download /></el-icon>导出报告
        </el-button>
      </div>

      <div v-if="summary" class="section">
        <div class="section-title">分析结论</div>
        <div class="summary-card">
          <div class="summary-text" v-html="formatText(summary)"></div>
        </div>
      </div>

      <!-- Basic Stats -->
      <div v-if="statsData.length > 0" class="section">
        <div class="section-title">关键指标</div>
        <div class="stats-grid">
          <div v-for="item in statsData" :key="item.col" class="stats-card">
            <div class="stats-card-header">{{ item.col }}</div>
            <div class="stats-items">
              <div class="stats-item">
                <span class="stats-label">均值</span>
                <span class="stats-value">{{ fmtNum(item.mean) }}</span>
              </div>
              <div class="stats-item">
                <span class="stats-label">中位数</span>
                <span class="stats-value">{{ fmtNum(item.median) }}</span>
              </div>
              <div class="stats-item">
                <span class="stats-label">总和</span>
                <span class="stats-value highlight">{{ fmtNum(item.sum) }}</span>
              </div>
              <div class="stats-item">
                <span class="stats-label">标准差</span>
                <span class="stats-value">{{ fmtNum(item.std) }}</span>
              </div>
              <div class="stats-item">
                <span class="stats-label">最小值</span>
                <span class="stats-value min">{{ fmtNum(item.min) }}</span>
              </div>
              <div class="stats-item">
                <span class="stats-label">最大值</span>
                <span class="stats-value max">{{ fmtNum(item.max) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Correlation -->
      <div v-if="correlationData" class="section">
        <div class="section-title">相关性分析</div>
        <div v-if="correlationData.top_correlations?.length" class="corr-list">
          <div v-for="(item, i) in correlationData.top_correlations" :key="i" class="corr-item">
            <div class="corr-pair">
              <span class="corr-col">{{ item.col1 }}</span>
              <span class="corr-arrow">—</span>
              <span class="corr-col">{{ item.col2 }}</span>
            </div>
            <div class="corr-bar-wrap">
              <div class="corr-bar" :style="corrBarStyle(item.correlation)"></div>
              <span class="corr-val" :class="corrClass(item.correlation)">
                {{ item.correlation > 0 ? '+' : '' }}{{ (item.correlation * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
        </div>
        <div v-else class="no-data">暂无显著相关性</div>
      </div>

      <!-- Anomaly -->
      <div v-if="anomalyData && Object.keys(anomalyData).length > 0" class="section">
        <div class="section-title">异常检测</div>
        <div v-for="(info, col) in anomalyData" :key="col" class="anomaly-card">
          <div class="anomaly-header">
            <span class="anomaly-col">{{ col }}</span>
            <el-tag type="danger" size="small">异常 {{ info.count }} 条</el-tag>
          </div>
          <div class="anomaly-range">
            正常范围: {{ fmtNum(info.lower_bound) }} ~ {{ fmtNum(info.upper_bound) }}
          </div>
          <el-table :data="info.anomalies" size="small" border stripe max-height="200">
            <el-table-column prop="index" label="行号" width="70" />
            <el-table-column label="异常值">
              <template #default="{ row }">
                <span class="anomaly-val">{{ fmtNum(row.value) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- Chat history analysis -->
      <div v-if="historyData.length > 0" class="section">
        <div class="section-title">对话分析结果</div>
        <div v-for="(item, i) in historyData" :key="i" class="history-card">
          <div class="history-title">{{ item.title }}</div>
          <div v-if="item.type === 'stats'" class="stats-grid compact">
            <div v-for="(colData, colName) in item.data" :key="colName" class="stats-card mini">
              <div class="stats-card-header">{{ colName }}</div>
              <div class="stats-items">
                <div class="stats-item" v-for="(v, k) in colData" :key="k">
                  <span class="stats-label">{{ metricLabels[k] || k }}</span>
                  <span class="stats-value">{{ typeof v === 'number' ? fmtNum(v) : v }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="history-raw">{{ formatRaw(item.data) }}</div>
        </div>
      </div>

      <div v-if="!summary && statsData.length === 0 && !correlationData && !anomalyData && historyData.length === 0" class="empty">
        <el-empty description="点击上方按钮开始分析" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { DataAnalysis, Connection, Warning, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../stores/app'
import { runAnalysis, exportReport as apiExportReport } from '../api'

const store = useAppStore()
const summary = ref('')
const rawMetrics = ref({})

const metricLabels = {
  count: '数量', mean: '均值', median: '中位数', std: '标准差',
  min: '最小值', max: '最大值', q25: 'Q25', q75: 'Q75', sum: '总和',
}

function fmtNum(v) {
  if (v == null || isNaN(v)) return '-'
  const n = Number(v)
  if (Math.abs(n) >= 10000) return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
  if (Math.abs(n) >= 1) return n.toLocaleString('zh-CN', { maximumFractionDigits: 4 })
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 6 })
}

function formatText(text) {
  return text.replace(/\n/g, '<br>')
}

function formatRaw(data) {
  if (typeof data === 'string') return data
  try { return JSON.stringify(data, null, 2) } catch { return String(data) }
}

// Parse basic_stats into array
const statsData = computed(() => {
  const bs = rawMetrics.value.basic_stats
  if (!bs || typeof bs !== 'object') return []
  return Object.entries(bs).map(([col, vals]) => ({
    col, ...vals,
  }))
})

// Parse correlation
const correlationData = computed(() => {
  const c = rawMetrics.value.correlation
  return c && typeof c === 'object' ? c : null
})

// Parse anomaly
const anomalyData = computed(() => {
  const a = rawMetrics.value.anomaly
  return a && typeof a === 'object' ? a : null
})

// Parse history analysis results
const historyData = computed(() => {
  const result = []
  for (const [key, val] of Object.entries(store.analysisResult)) {
    if (key === 'basic_stats' || key === 'correlation' || key === 'anomaly') continue
    if (val && typeof val === 'object' && !Array.isArray(val)) {
      result.push({ title: key, data: val, type: typeof val === 'object' ? 'stats' : 'raw' })
    }
  }
  return result
})

function corrClass(val) {
  if (val >= 0.7) return 'strong-pos'
  if (val >= 0.4) return 'moderate-pos'
  if (val >= 0) return 'weak-pos'
  if (val >= -0.4) return 'weak-neg'
  if (val >= -0.7) return 'moderate-neg'
  return 'strong-neg'
}

function corrBarStyle(val) {
  const pct = Math.abs(val) * 100
  const color = val >= 0 ? '#67c23a' : '#f56c6c'
  return { width: pct + '%', backgroundColor: color }
}

async function runBasicStats() {
  try {
    const { data } = await runAnalysis({ analysis_type: 'basic_stats' })
    summary.value = data.summary
    rawMetrics.value = { ...rawMetrics.value, ...data.metrics }
    store.analysisResult = { ...store.analysisResult, ...data.metrics }
    ElMessage.success('基础统计完成')
  } catch (e) { ElMessage.error('分析失败') }
}

async function runCorrelation() {
  try {
    const { data } = await runAnalysis({ analysis_type: 'correlation' })
    rawMetrics.value = { ...rawMetrics.value, ...data.metrics }
    store.analysisResult = { ...store.analysisResult, ...data.metrics }
    ElMessage.success('相关性分析完成')
  } catch (e) { ElMessage.error('分析失败') }
}

async function runAnomaly() {
  try {
    const { data } = await runAnalysis({ analysis_type: 'anomaly' })
    rawMetrics.value = { ...rawMetrics.value, ...data.metrics }
    store.analysisResult = { ...store.analysisResult, ...data.metrics }
    ElMessage.success('异常检测完成')
  } catch (e) { ElMessage.error('分析失败') }
}

async function exportReport() {
  try {
    const resp = await apiExportReport({ format: 'html' })
    const url = URL.createObjectURL(new Blob([resp.data]))
    const a = document.createElement('a')
    a.href = url; a.download = 'report.html'; a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('报告导出成功')
  } catch (e) { ElMessage.error('导出失败') }
}
</script>

<style scoped>
.analysis-container { height: 100%; overflow: auto; padding: 4px; }
.toolbar { margin-bottom: 16px; display: flex; gap: 8px; flex-wrap: wrap; }
.empty { display: flex; align-items: center; justify-content: center; height: 400px; }

.section { margin-bottom: 20px; }
.section-title {
  font-size: 15px; font-weight: 600; color: #1a1a2e;
  padding-bottom: 8px; margin-bottom: 12px;
  border-bottom: 2px solid #409eff;
  display: flex; align-items: center; gap: 6px;
}

/* Summary */
.summary-card {
  background: linear-gradient(135deg, #f0f7ff 0%, #e8f4fd 100%);
  border-radius: 8px; padding: 16px 20px;
  border-left: 4px solid #409eff;
}
.summary-text { font-size: 14px; line-height: 1.8; color: #333; }

/* Stats cards */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.stats-grid.compact { grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
.stats-card {
  background: #fff; border-radius: 8px; overflow: hidden;
  border: 1px solid #e4e7ed; transition: box-shadow 0.2s;
}
.stats-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.stats-card.mini { border: 1px solid #ebeef5; }
.stats-card-header {
  background: linear-gradient(90deg, #409eff 0%, #66b1ff 100%);
  color: #fff; padding: 8px 14px; font-size: 13px; font-weight: 600;
}
.stats-items { padding: 10px 14px; }
.stats-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 5px 0; border-bottom: 1px dashed #f0f0f0;
}
.stats-item:last-child { border-bottom: none; }
.stats-label { font-size: 12px; color: #909399; }
.stats-value { font-size: 13px; font-weight: 600; color: #303133; font-variant-numeric: tabular-nums; }
.stats-value.highlight { color: #409eff; font-size: 14px; }
.stats-value.min { color: #e6a23c; }
.stats-value.max { color: #67c23a; }

/* Correlation */
.corr-list { display: flex; flex-direction: column; gap: 8px; }
.corr-item {
  display: flex; align-items: center; gap: 12px;
  background: #fafafa; border-radius: 6px; padding: 10px 14px;
}
.corr-pair { display: flex; align-items: center; gap: 6px; min-width: 160px; }
.corr-col { font-size: 13px; font-weight: 500; color: #303133; background: #ecf5ff; padding: 2px 8px; border-radius: 4px; }
.corr-arrow { color: #c0c4cc; }
.corr-bar-wrap { flex: 1; display: flex; align-items: center; gap: 8px; }
.corr-bar { height: 8px; border-radius: 4px; transition: width 0.5s ease; min-width: 4px; }
.corr-val { font-size: 13px; font-weight: 600; min-width: 60px; text-align: right; font-variant-numeric: tabular-nums; }
.corr-val.strong-pos { color: #67c23a; }
.corr-val.moderate-pos { color: #95d475; }
.corr-val.weak-pos { color: #b3e19d; }
.corr-val.weak-neg { color: #f89898; }
.corr-val.moderate-neg { color: #f56c6c; }
.corr-val.strong-neg { color: #c45656; }
.no-data { color: #909399; text-align: center; padding: 20px; }

/* Anomaly */
.anomaly-card {
  background: #fff; border: 1px solid #fde2e2; border-radius: 8px;
  padding: 14px; margin-bottom: 12px;
}
.anomaly-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.anomaly-col { font-weight: 600; color: #303133; font-size: 14px; }
.anomaly-range { font-size: 12px; color: #909399; margin-bottom: 10px; }
.anomaly-val { color: #f56c6c; font-weight: 600; }

/* History */
.history-card { background: #fafafa; border-radius: 8px; padding: 14px; margin-bottom: 12px; }
.history-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 10px; }
.history-raw {
  background: #f5f7fa; padding: 12px; border-radius: 6px;
  font-size: 12px; overflow-x: auto; white-space: pre-wrap; font-family: monospace;
  max-height: 300px; overflow-y: auto;
}
</style>
