<template>
  <div class="chart-container">
    <div v-if="store.charts.length === 0" class="empty">
      <el-empty description="暂无图表，请上传数据后发送分析指令" />
    </div>
    <div v-else>
      <div class="chart-header">
        <span class="chart-count">共 {{ store.charts.length }} 张图表</span>
        <el-button size="small" type="danger" text @click="clearAll">清空全部</el-button>
      </div>
      <div class="chart-grid">
        <div v-for="(chart, idx) in store.charts" :key="idx" class="chart-item">
          <div class="chart-toolbar">
            <span class="chart-title">{{ chartTitle(chart) }}</span>
            <div class="chart-btns">
              <el-button size="small" text @click="openEdit(idx)"><el-icon><Edit /></el-icon></el-button>
              <el-button size="small" text @click="downloadPng(idx)"><el-icon><Download /></el-icon> PNG</el-button>
              <el-button size="small" text @click="downloadSvg(idx)"><el-icon><Download /></el-icon> SVG</el-button>
              <el-button size="small" text type="danger" @click="removeChart(idx)"><el-icon><Delete /></el-icon></el-button>
            </div>
          </div>
          <div :ref="el => setChartRef(el, idx)" class="chart-box"></div>
        </div>
      </div>
    </div>

    <!-- Edit Dialog -->
    <el-dialog v-model="editVisible" title="编辑图表" width="480px" destroy-on-close>
      <el-form label-width="80px" size="small">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" placeholder="图表标题" />
        </el-form-item>
        <el-form-item label="图表类型">
          <el-select v-model="editForm.chartType" style="width: 100%">
            <el-option label="折线图" value="line" />
            <el-option label="柱状图" value="bar" />
            <el-option label="面积图" value="area" />
            <el-option label="饼图" value="pie" />
            <el-option label="散点图" value="scatter" />
          </el-select>
        </el-form-item>
        <el-form-item label="配色方案">
          <div class="color-themes">
            <div v-for="(theme, i) in colorThemes" :key="i"
              class="color-theme" :class="{ active: editForm.themeIndex === i }"
              @click="editForm.themeIndex = i">
              <span v-for="c in theme.slice(0, 5)" :key="c" class="color-dot" :style="{ background: c }"></span>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="applyEdit">应用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Download, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const chartRefs = ref({})
const chartInstances = ref({})
const mapsLoaded = ref(false)

const colorThemes = [
  ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4'],
  ['#c1232b', '#27727b', '#fcce10', '#e87c25', '#b5c334', '#fe8463', '#9bca63', '#fad860'],
  ['#1abc9c', '#2ecc71', '#3498db', '#9b59b6', '#f1c40f', '#e67e22', '#e74c3c', '#34495e'],
  ['#8dd3c7', '#ffffb3', '#bebada', '#fb8072', '#80b1d3', '#fdb462', '#b3de69', '#fccde5'],
  ['#67001f', '#b2182b', '#d6604d', '#f4a582', '#fddbc7', '#d1e5f0', '#92c5de', '#4393c3'],
]

const editVisible = ref(false)
const editForm = reactive({ index: 0, title: '', chartType: 'bar', themeIndex: 0 })
let currentPlotlyData = null

function setChartRef(el, idx) {
  if (el) chartRefs.value[idx] = el
}

function chartTitle(plotlyData) {
  if (!plotlyData) return ''
  if (plotlyData.chart_type && plotlyData.echarts_option) {
    return plotlyData.title || plotlyData.echarts_option?.title?.text || ''
  }
  const layout = plotlyData.layout || {}
  return layout.title?.text || ''
}

function formatDateLabel(val) {
  if (typeof val === 'string' && val.length >= 10) return val.slice(0, 10)
  return val
}

function convertPlotlyToEcharts(plotlyData, themeIdx = 0) {
  if (!plotlyData) return null

  // 地图类型直接返回 echarts_option
  if (plotlyData.chart_type && plotlyData.echarts_option) {
    return plotlyData.echarts_option
  }

  if (!plotlyData.data || !plotlyData.data.length) return null

  const traces = plotlyData.data
  const layout = plotlyData.layout || {}
  const firstTrace = traces[0]
  const traceType = firstTrace.type || 'scatter'
  const mode = firstTrace.mode || ''
  const colors = colorThemes[themeIdx] || colorThemes[0]
  const title = layout.title?.text || ''

  // Line (scatter with lines mode)
  if (traceType === 'scatter' && (mode.includes('lines') || mode.includes('marker'))) {
    const xData = (firstTrace.x || []).map(formatDateLabel)
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { data: traces.map(t => t.name).filter(Boolean), top: 30 },
      grid: { left: 60, right: 20, top: 60, bottom: 40 },
      xAxis: { type: 'category', data: xData, axisLabel: { rotate: xData.length > 10 ? 30 : 0 } },
      yAxis: { type: 'value' },
      series: traces.map((t, i) => ({
        name: t.name || '', type: 'line', data: t.y, smooth: true,
        itemStyle: { color: colors[i % colors.length] }, lineStyle: { width: 2 },
      })),
    }
  }

  // Bar
  if (traceType === 'bar') {
    const xData = (firstTrace.x || []).map(formatDateLabel)
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { data: traces.map(t => t.name).filter(Boolean), top: 30 },
      grid: { left: 60, right: 20, top: 60, bottom: 40 },
      xAxis: { type: 'category', data: xData },
      yAxis: { type: 'value' },
      series: traces.map((t, i) => ({
        name: t.name || '', type: 'bar', data: t.y,
        itemStyle: { color: colors[i % colors.length] },
      })),
    }
  }

  // Pie
  if (traceType === 'pie') {
    const pieData = firstTrace.labels.map((label, i) => ({
      name: label, value: firstTrace.values[i],
      itemStyle: { color: colors[i % colors.length] },
    }))
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item' },
      legend: { top: 30 },
      series: [{
        type: 'pie', radius: ['35%', '60%'], center: ['50%', '55%'], data: pieData,
        label: { formatter: '{b}\n{d}%' },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
      }],
    }
  }

  // Scatter (pure)
  if (traceType === 'scatter') {
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item' },
      xAxis: { type: 'value' },
      yAxis: { type: 'value' },
      series: traces.map((t, i) => ({
        type: 'scatter', data: t.x?.map((x, j) => [x, t.y[j]]) || [],
        itemStyle: { color: colors[i % colors.length] },
      })),
    }
  }

  // Heatmap
  if (traceType === 'heatmap') {
    const xLabels = firstTrace.x || []
    const yLabels = firstTrace.y || []
    const zData = firstTrace.z || []
    const data = []
    for (let i = 0; i < yLabels.length; i++)
      for (let j = 0; j < xLabels.length; j++)
        data.push([j, i, zData[i]?.[j] ?? 0])
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { formatter: p => `${yLabels[p.data[1]]} / ${xLabels[p.data[0]]}: ${p.data[2]?.toFixed(4)}` },
      xAxis: { type: 'category', data: xLabels, axisLabel: { rotate: 30 } },
      yAxis: { type: 'category', data: yLabels },
      grid: { left: 80, right: 20, top: 40, bottom: 80 },
      visualMap: {
        min: -1, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 10,
        inRange: { color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#fdae61', '#f46d43', '#d73027'] },
      },
      series: [{ type: 'heatmap', data, label: { show: xLabels.length <= 10, formatter: p => p.data[2]?.toFixed(2) } }],
    }
  }

  // Box plot
  if (traceType === 'box') {
    const boxData = traces.map((t, i) => ({
      name: t.name || `系列${i + 1}`,
      type: 'boxplot',
      data: t.y ? [calcBoxStats(t.y)] : [],
      itemStyle: { color: colors[i % colors.length] },
    }))
    const xData = traces.map(t => t.name || '')
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item' },
      xAxis: { type: 'category', data: xData },
      yAxis: { type: 'value' },
      series: boxData.length && boxData[0].data[0] ? boxData : [{
        type: 'boxplot',
        data: traces.map(t => {
          const vals = (t.y || []).filter(v => v != null && !isNaN(v)).sort((a, b) => a - b)
          if (!vals.length) return [0, 0, 0, 0, 0]
          const q1 = quantile(vals, 0.25)
          const q2 = quantile(vals, 0.5)
          const q3 = quantile(vals, 0.75)
          const iqr = q3 - q1
          return [q1 - 1.5 * iqr, q1, q2, q3, q3 + 1.5 * iqr]
        }),
        itemStyle: { color: colors[0] },
      }],
    }
  }

  // Area (scatter with fill)
  if (traceType === 'scatter' && firstTrace.fill) {
    const xData = (firstTrace.x || []).map(formatDateLabel)
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { data: traces.map(t => t.name).filter(Boolean), top: 30 },
      grid: { left: 60, right: 20, top: 60, bottom: 40 },
      xAxis: { type: 'category', data: xData },
      yAxis: { type: 'value' },
      series: traces.map((t, i) => ({
        name: t.name || '', type: 'line', data: t.y, smooth: true,
        areaStyle: { opacity: 0.3 },
        itemStyle: { color: colors[i % colors.length] },
      })),
    }
  }

  // Scatterpolar (radar)
  if (traceType === 'scatterpolar') {
    const categories = firstTrace.theta || []
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: {},
      radar: { indicator: categories.map(c => ({ name: c, max: Math.max(...(firstTrace.r || [1])) * 1.2 })) },
      series: [{
        type: 'radar',
        data: traces.map((t, i) => ({
          name: t.name || '',
          value: t.r || [],
          areaStyle: { opacity: 0.2 },
          lineStyle: { color: colors[i % colors.length] },
          itemStyle: { color: colors[i % colors.length] },
        })),
      }],
    }
  }

  // Fallback
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: (firstTrace.x || []).map(formatDateLabel) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: firstTrace.y, itemStyle: { color: colorThemes[0][0] } }],
  }
}

function quantile(sorted, q) {
  const pos = (sorted.length - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  return sorted[base + 1] !== undefined
    ? sorted[base] + rest * (sorted[base + 1] - sorted[base])
    : sorted[base]
}

function calcBoxStats(values) {
  const sorted = values.filter(v => v != null && !isNaN(v)).sort((a, b) => a - b)
  if (!sorted.length) return [0, 0, 0, 0, 0]
  const q1 = quantile(sorted, 0.25)
  const q2 = quantile(sorted, 0.5)
  const q3 = quantile(sorted, 0.75)
  const iqr = q3 - q1
  return [q1 - 1.5 * iqr, q1, q2, q3, q3 + 1.5 * iqr]
}

async function loadMaps() {
  if (mapsLoaded.value) return
  try {
    const [chinaResp, worldResp] = await Promise.all([
      fetch('/china.json').then(r => r.json()).catch(() => null),
      fetch('/world.json').then(r => r.json()).catch(() => null),
    ])
    if (chinaResp) echarts.registerMap('china', chinaResp)
    if (worldResp) echarts.registerMap('world', worldResp)
    mapsLoaded.value = true
  } catch (e) {
    console.warn('地图数据加载失败:', e)
  }
}

function renderCharts() {
  nextTick(() => {
    store.charts.forEach((chartData, idx) => {
      const el = chartRefs.value[idx]
      if (!el) return
      if (chartInstances.value[idx]) chartInstances.value[idx].dispose()

      // 地图类型需要先加载地图数据
      if (chartData.chart_type === 'china_map' || chartData.chart_type === 'world_map') {
        loadMaps().then(() => {
          const opt = convertPlotlyToEcharts(chartData)
          if (opt) {
            const inst = echarts.init(el)
            inst.setOption(opt)
            chartInstances.value[idx] = inst
          }
        })
        return
      }

      const opt = convertPlotlyToEcharts(chartData)
      if (opt) {
        const inst = echarts.init(el)
        inst.setOption(opt)
        chartInstances.value[idx] = inst
      }
    })
  })
}

function downloadPng(idx) {
  const inst = chartInstances.value[idx]
  if (!inst) return
  const url = inst.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' })
  const a = document.createElement('a')
  a.href = url; a.download = `chart_${idx + 1}.png`; a.click()
  ElMessage.success('PNG 已下载')
}

function downloadSvg(idx) {
  const inst = chartInstances.value[idx]
  if (!inst) return
  const url = inst.getDataURL({ type: 'svg' })
  const a = document.createElement('a')
  a.href = url; a.download = `chart_${idx + 1}.svg`; a.click()
  ElMessage.success('SVG 已下载')
}

function removeChart(idx) {
  store.removeChart(idx)
  if (chartInstances.value[idx]) {
    chartInstances.value[idx].dispose()
    delete chartInstances.value[idx]
  }
  ElMessage.success('图表已删除')
}

async function clearAll() {
  try {
    await ElMessageBox.confirm('确定清空所有图表？', '确认')
    store.setCharts([])
    Object.values(chartInstances.value).forEach(inst => inst?.dispose())
    chartInstances.value = {}
    ElMessage.success('已清空')
  } catch (_) {}
}

function openEdit(idx) {
  const chart = store.charts[idx]
  if (!chart) return
  currentPlotlyData = chart
  editForm.index = idx
  editForm.title = chartTitle(chart)
  editForm.themeIndex = 0
  // Determine current chart type
  if (chart.chart_type) {
    editForm.chartType = chart.chart_type
  } else if (chart.data?.[0]) {
    const t = chart.data[0].type || 'scatter'
    const m = chart.data[0].mode || ''
    if (t === 'scatter' && (m.includes('lines') || m.includes('marker'))) editForm.chartType = 'line'
    else if (t === 'scatterpolar') editForm.chartType = 'radar'
    else editForm.chartType = t
  } else {
    editForm.chartType = 'bar'
  }
  editVisible.value = true
}

function applyEdit() {
  const idx = editForm.index
  const chart = store.charts[idx]
  if (!chart) return

  // Update title
  if (chart.echarts_option) {
    // Map chart - update title directly
    chart.title = editForm.title
    if (chart.echarts_option.title) chart.echarts_option.title.text = editForm.title
  } else if (chart.layout) {
    chart.layout.title = { text: editForm.title }
  }

  // For non-map charts, change type if needed
  if (!chart.chart_type && chart.data?.[0]) {
    const trace = chart.data[0]
    const typeMap = { line: 'scatter', bar: 'bar', pie: 'pie', scatter: 'scatter', area: 'scatter' }
    const newType = typeMap[editForm.chartType] || 'bar'
    trace.type = newType
    if (editForm.chartType === 'line') {
      trace.mode = 'lines+markers'
      trace.fill = undefined
    } else if (editForm.chartType === 'area') {
      trace.type = 'scatter'
      trace.mode = 'lines'
      trace.fill = 'tozeroy'
    } else if (editForm.chartType === 'bar') {
      trace.mode = undefined
      trace.fill = undefined
    } else if (editForm.chartType === 'scatter') {
      trace.mode = 'markers'
      trace.fill = undefined
    }
  }

  // Apply theme
  const theme = colorThemes[editForm.themeIndex]
  if (chart.data) {
    chart.data.forEach((trace, i) => {
      if (!trace.marker) trace.marker = {}
      trace.marker.color = theme[i % theme.length]
    })
  }

  store.updateChartAt(idx, { ...chart })
  editVisible.value = false
  ElMessage.success('图表已更新')
}

watch(() => store.charts, renderCharts, { deep: true })
onMounted(renderCharts)
</script>

<style scoped>
.chart-container { height: 100%; overflow: auto; }
.chart-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px; padding: 0 4px;
}
.chart-count { font-size: 13px; color: #606266; }
.chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(480px, 1fr)); gap: 16px; }
.chart-item {
  background: #fff; border-radius: 10px; overflow: hidden;
  border: 1px solid #e4e7ed; transition: box-shadow 0.2s;
}
.chart-item:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.chart-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 14px; background: #fafafa; border-bottom: 1px solid #eee;
}
.chart-title { font-size: 13px; font-weight: 600; color: #303133; }
.chart-btns { display: flex; gap: 2px; }
.chart-box { width: 100%; height: 360px; padding: 8px; }
.empty { display: flex; align-items: center; justify-content: center; height: 400px; }

.color-themes { display: flex; gap: 10px; flex-wrap: wrap; }
.color-theme {
  display: flex; gap: 3px; padding: 6px 8px; border-radius: 6px;
  border: 2px solid transparent; cursor: pointer; transition: all 0.15s;
}
.color-theme:hover { border-color: #c0c4cc; }
.color-theme.active { border-color: #409eff; background: #ecf5ff; }
.color-dot { width: 14px; height: 14px; border-radius: 3px; }
</style>
