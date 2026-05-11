<template>
  <div class="cleaning-container">
    <div v-if="!store.hasData" class="empty">
      <el-empty description="请先上传数据文件" />
    </div>
    <div v-else class="cleaning-content">
      <!-- AI Recommend -->
      <el-card shadow="hover" class="section-card ai-card">
        <template #header>
          <div class="section-header-row">
            <span class="section-title">AI 智能推荐</span>
            <el-button type="primary" size="small" @click="getRecommendations" :loading="loading.recommend">
              获取推荐
            </el-button>
          </div>
        </template>
        <div v-if="!recommendSteps.length && !loading.recommend" class="ai-hint">
          <el-text type="info">点击"获取推荐"，AI 将分析数据并推荐清洗步骤</el-text>
        </div>
        <div v-if="recommendSteps.length" class="recommend-list">
          <div v-for="(step, idx) in recommendSteps" :key="idx" class="recommend-item">
            <el-checkbox v-model="step.checked" />
            <div class="recommend-content">
              <div class="recommend-label">{{ step.label }}</div>
              <div class="recommend-reason">{{ step.reason }}</div>
            </div>
          </div>
          <el-button type="success" size="small" @click="executeRecommendations"
            :loading="loading.execRecommend" style="margin-top: 8px">
            执行选中步骤 ({{ recommendSteps.filter(s => s.checked).length }})
          </el-button>
        </div>
      </el-card>

      <!-- AI Advanced Transform -->
      <el-card shadow="hover" class="section-card ai-card">
        <template #header>
          <span class="section-title">AI 智能处理</span>
        </template>
        <div class="nl-input-row">
          <el-input
            v-model="nlInstruction"
            type="textarea"
            :rows="2"
            placeholder="用自然语言描述数据处理需求，AI 会自动生成代码执行，例如：&#10;- 新增利润率列，利润率=利润/销售额&#10;- 按地区统计总销售额和总利润&#10;- 把销售额大于1000的标记为高销售&#10;- 提取日期列的月份信息&#10;- 把产品A和产品B的数据筛选出来"
          />
          <el-button type="primary" @click="runAiClean" :loading="loading.aiClean"
            :disabled="!nlInstruction.trim()">
            执行
          </el-button>
        </div>
      </el-card>

      <!-- Quick actions -->
      <el-card shadow="hover" class="section-card">
        <template #header>
          <span class="section-title">快速清洗</span>
        </template>
        <div class="quick-actions">
          <el-button type="primary" @click="runAutoClean" :loading="loading.auto">
            一键自动清洗
          </el-button>
          <el-button @click="runDropDuplicates" :loading="loading.dedup">
            去除重复值
          </el-button>
          <el-button @click="runTrim" :loading="loading.trim">
            去除首尾空白
          </el-button>
        </div>
      </el-card>

      <!-- Fill missing values -->
      <el-card shadow="hover" class="section-card">
        <template #header>
          <span class="section-title">缺失值处理</span>
        </template>
        <el-form :inline="true" size="small">
          <el-form-item label="方法">
            <el-select v-model="fillForm.method" style="width: 140px">
              <el-option label="均值填充" value="mean" />
              <el-option label="中位数填充" value="median" />
              <el-option label="众数填充" value="mode" />
              <el-option label="指定值填充" value="value" />
              <el-option label="前向填充" value="forward" />
              <el-option label="后向填充" value="backward" />
              <el-option label="删除缺失行" value="drop" />
            </el-select>
          </el-form-item>
          <el-form-item label="列" v-if="fillForm.method !== 'value'">
            <el-select v-model="fillForm.columns" multiple collapse-tags placeholder="全部列" style="width: 220px">
              <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
            </el-select>
          </el-form-item>
          <el-form-item label="填充值" v-if="fillForm.method === 'value'">
            <el-input v-model="fillForm.value" placeholder="输入填充值" style="width: 140px" />
          </el-form-item>
          <el-form-item label="列" v-if="fillForm.method === 'value'">
            <el-select v-model="fillForm.columns" multiple collapse-tags placeholder="选择列" style="width: 220px">
              <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="runFillMissing" :loading="loading.fill">执行</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Remove outliers -->
      <el-card shadow="hover" class="section-card">
        <template #header>
          <span class="section-title">异常值处理</span>
        </template>
        <el-form :inline="true" size="small">
          <el-form-item label="方法">
            <el-select v-model="outlierForm.method" style="width: 140px">
              <el-option label="IQR法" value="iqr" />
              <el-option label="Z-Score法" value="zscore" />
            </el-select>
          </el-form-item>
          <el-form-item label="列">
            <el-select v-model="outlierForm.columns" multiple collapse-tags placeholder="全部数值列" style="width: 220px">
              <el-option v-for="col in numericColumns" :key="col" :label="col" :value="col" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="runRemoveOutliers" :loading="loading.outlier">执行</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Text processing -->
      <el-card shadow="hover" class="section-card">
        <template #header>
          <span class="section-title">文本处理</span>
        </template>
        <el-form :inline="true" size="small">
          <el-form-item label="操作">
            <el-select v-model="textForm.case" style="width: 140px">
              <el-option label="转小写" value="lower" />
              <el-option label="转大写" value="upper" />
              <el-option label="首字母大写" value="title" />
            </el-select>
          </el-form-item>
          <el-form-item label="列">
            <el-select v-model="textForm.columns" multiple collapse-tags placeholder="全部文本列" style="width: 220px">
              <el-option v-for="col in textColumns" :key="col" :label="col" :value="col" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="runStandardizeCase" :loading="loading.case">执行</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Type conversion -->
      <el-card shadow="hover" class="section-card">
        <template #header>
          <span class="section-title">类型转换</span>
        </template>
        <el-form :inline="true" size="small">
          <el-form-item label="列">
            <el-select v-model="convertForm.column" placeholder="选择列" style="width: 180px">
              <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
            </el-select>
          </el-form-item>
          <el-form-item label="目标类型">
            <el-select v-model="convertForm.target_type" style="width: 120px">
              <el-option label="整数" value="int" />
              <el-option label="浮点数" value="float" />
              <el-option label="字符串" value="str" />
              <el-option label="日期时间" value="datetime" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="runConvert" :loading="loading.convert">执行</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Datetime truncation -->
      <el-card shadow="hover" class="section-card">
        <template #header>
          <span class="section-title">时间格式截断</span>
        </template>
        <el-form :inline="true" size="small">
          <el-form-item label="格式">
            <el-select v-model="dtForm.fmt" style="width: 140px">
              <el-option label="年-月" value="%Y-%m" />
              <el-option label="年-月-日" value="%Y-%m-%d" />
              <el-option label="年" value="%Y" />
            </el-select>
          </el-form-item>
          <el-form-item label="列">
            <el-select v-model="dtForm.columns" multiple collapse-tags placeholder="全部日期列" style="width: 220px">
              <el-option v-for="col in dateColumns" :key="col" :label="col" :value="col" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="runTruncateDatetime" :loading="loading.truncate">执行</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Drop rows by condition -->
      <el-card shadow="hover" class="section-card">
        <template #header>
          <span class="section-title">条件筛选删除</span>
        </template>
        <el-form :inline="true" size="small">
          <el-form-item label="列">
            <el-select v-model="dropForm.column" placeholder="选择列" style="width: 160px">
              <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
            </el-select>
          </el-form-item>
          <el-form-item label="条件">
            <el-select v-model="dropForm.operator" style="width: 110px">
              <el-option label="等于" value="==" />
              <el-option label="不等于" value="!=" />
              <el-option label="大于" value=">" />
              <el-option label="大于等于" value=">=" />
              <el-option label="小于" value="<" />
              <el-option label="小于等于" value="<=" />
              <el-option label="包含" value="contains" />
              <el-option label="不包含" value="not_contains" />
            </el-select>
          </el-form-item>
          <el-form-item label="值">
            <el-input v-model="dropForm.value" placeholder="输入值" style="width: 140px" />
          </el-form-item>
          <el-form-item>
            <el-button type="danger" @click="runDropRows" :loading="loading.drop">删除</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Drop columns -->
      <el-card shadow="hover" class="section-card">
        <template #header>
          <span class="section-title">删除列</span>
        </template>
        <el-form :inline="true" size="small">
          <el-form-item label="选择列">
            <el-select v-model="dropColForm.columns" multiple collapse-tags placeholder="选择要删除的列" style="width: 300px">
              <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="danger" @click="runDropColumns" :loading="loading.dropCol">删除列</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Rename columns -->
      <el-card shadow="hover" class="section-card">
        <template #header>
          <div class="section-header-row">
            <span class="section-title">重命名列</span>
            <el-button size="small" text @click="addRenameItem">+ 添加</el-button>
          </div>
        </template>
        <div v-if="renameForm.items.length === 0" class="empty-hint">
          <el-text type="info" size="small">点击"添加"设置列重命名映射</el-text>
        </div>
        <div v-for="(item, idx) in renameForm.items" :key="idx" class="rename-row">
          <el-select v-model="item.from" placeholder="原列名" style="width: 180px" size="small">
            <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
          </el-select>
          <el-text class="rename-arrow">→</el-text>
          <el-input v-model="item.to" placeholder="新列名" style="width: 180px" size="small" />
          <el-button size="small" text type="danger" @click="renameForm.items.splice(idx, 1)">移除</el-button>
        </div>
        <div v-if="renameForm.items.length > 0" style="margin-top: 8px">
          <el-button type="primary" size="small" @click="runRename" :loading="loading.rename">执行重命名</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '../stores/app'
import * as api from '../api'

const store = useAppStore()
const columns = computed(() => store.dataInfo?.column_names || [])
const dtypes = computed(() => store.dataInfo?.dtypes || {})

const numericColumns = computed(() =>
  columns.value.filter(c => {
    const dt = dtypes.value[c] || ''
    return dt.includes('int') || dt.includes('float') || dt.includes('number')
  })
)
const textColumns = computed(() =>
  columns.value.filter(c => (dtypes.value[c] || '').includes('object'))
)
const dateColumns = computed(() =>
  columns.value.filter(c => (dtypes.value[c] || '').includes('datetime'))
)

const loading = ref({
  auto: false, dedup: false, trim: false, fill: false,
  outlier: false, case: false, convert: false, drop: false,
  dropCol: false, rename: false, recommend: false, execRecommend: false, aiClean: false,
  truncate: false,
})

const recommendSteps = ref([])
const nlInstruction = ref('')
const fillForm = ref({ method: 'mean', columns: [], value: '' })
const outlierForm = ref({ method: 'iqr', columns: [] })
const textForm = ref({ case: 'lower', columns: [] })
const convertForm = ref({ column: '', target_type: 'str' })
const dropForm = ref({ column: '', operator: '==', value: '' })
const dropColForm = ref({ columns: [] })
const renameForm = ref({ items: [] })
const dtForm = ref({ fmt: '%Y-%m', columns: [] })

function handleResult(data) {
  if (data.error) {
    ElMessage.error(data.error)
    return
  }
  if (data.info) {
    store.dataInfo = data.info
  }
  if (data.preview) {
    store.previewData = data.preview
  }
  ElMessage.success(data.message || '操作成功')
}

function handleError(e) {
  ElMessage.error('操作失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
}

// --- AI Recommend ---
async function getRecommendations() {
  loading.value.recommend = true
  recommendSteps.value = []
  try {
    const { data } = await api.cleanRecommend()
    if (data.error) {
      ElMessage.error(data.error)
      return
    }
    const steps = data.steps || []
    if (!steps.length) {
      ElMessage.info('AI 未发现需要清洗的问题，数据质量良好')
      return
    }
    recommendSteps.value = steps.map(s => ({
      ...s,
      checked: true,
    }))
    ElMessage.success(`AI 推荐了 ${steps.length} 个清洗步骤`)
  } catch (e) {
    handleError(e)
  } finally {
    loading.value.recommend = false
  }
}

async function executeRecommendations() {
  const selected = recommendSteps.value.filter(s => s.checked)
  if (!selected.length) {
    ElMessage.warning('请至少选择一个步骤')
    return
  }
  loading.value.execRecommend = true
  try {
    const { data } = await api.cleanExecuteSteps({ steps: selected })
    handleResult(data)
    recommendSteps.value = []
  } catch (e) {
    handleError(e)
  } finally {
    loading.value.execRecommend = false
  }
}

// --- AI Natural Language Clean ---
async function runAiClean() {
  const instruction = nlInstruction.value.trim()
  if (!instruction) return
  loading.value.aiClean = true
  try {
    const { data } = await api.cleanAiTransform({ instruction })
    handleResult(data)
    nlInstruction.value = ''
  } catch (e) {
    handleError(e)
  } finally {
    loading.value.aiClean = false
  }
}

// --- Manual operations ---
async function runAutoClean() {
  loading.value.auto = true
  try {
    const { data } = await api.cleanAuto()
    handleResult(data)
  } catch (e) { handleError(e) } finally { loading.value.auto = false }
}

async function runDropDuplicates() {
  loading.value.dedup = true
  try {
    const { data } = await api.cleanDropDuplicates()
    handleResult(data)
  } catch (e) { handleError(e) } finally { loading.value.dedup = false }
}

async function runTrim() {
  loading.value.trim = true
  try {
    const { data } = await api.cleanTrim()
    handleResult(data)
  } catch (e) { handleError(e) } finally { loading.value.trim = false }
}

async function runFillMissing() {
  const m = fillForm.value.method
  loading.value.fill = true
  try {
    let data
    const cols = fillForm.value.columns.length ? fillForm.value.columns : null
    if (m === 'value') {
      const res = await api.cleanFillValue({ columns: fillForm.value.columns, value: fillForm.value.value })
      data = res.data
    } else if (m === 'forward') {
      const res = await api.cleanFillForward({ columns: cols })
      data = res.data
    } else if (m === 'backward') {
      const res = await api.cleanFillBackward({ columns: cols })
      data = res.data
    } else if (m === 'mode') {
      const res = await api.cleanFillMissing({ columns: cols, method: 'mode' })
      data = res.data
    } else {
      const res = await api.cleanFillMissing({ columns: cols, method: m })
      data = res.data
    }
    handleResult(data)
  } catch (e) { handleError(e) } finally { loading.value.fill = false }
}

async function runRemoveOutliers() {
  loading.value.outlier = true
  try {
    const cols = outlierForm.value.columns.length ? outlierForm.value.columns : null
    const { data } = await api.cleanRemoveOutliers({ columns: cols, method: outlierForm.value.method })
    handleResult(data)
  } catch (e) { handleError(e) } finally { loading.value.outlier = false }
}

async function runStandardizeCase() {
  loading.value.case = true
  try {
    const cols = textForm.value.columns.length ? textForm.value.columns : null
    const { data } = await api.cleanStandardizeCase({ columns: cols, case: textForm.value.case })
    handleResult(data)
  } catch (e) { handleError(e) } finally { loading.value.case = false }
}

async function runConvert() {
  if (!convertForm.value.column) {
    ElMessage.warning('请选择要转换的列')
    return
  }
  loading.value.convert = true
  try {
    const { data } = await api.cleanConvert({
      column: convertForm.value.column,
      target_type: convertForm.value.target_type,
    })
    handleResult(data)
  } catch (e) { handleError(e) } finally { loading.value.convert = false }
}

async function runTruncateDatetime() {
  loading.value.truncate = true
  try {
    const cols = dtForm.value.columns.length ? dtForm.value.columns : null
    const { data } = await api.cleanTruncateDatetime({ columns: cols, fmt: dtForm.value.fmt })
    handleResult(data)
  } catch (e) { handleError(e) } finally { loading.value.truncate = false }
}

async function runDropRows() {
  if (!dropForm.value.column) {
    ElMessage.warning('请选择列')
    return
  }
  try {
    await ElMessageBox.confirm('确定要按条件删除数据行吗？此操作不可撤销。', '确认')
    loading.value.drop = true
    const { data } = await api.cleanDropRows({
      column: dropForm.value.column,
      operator: dropForm.value.operator,
      value: dropForm.value.value,
    })
    handleResult(data)
  } catch (e) { if (e !== 'cancel') handleError(e) } finally { loading.value.drop = false }
}

async function runDropColumns() {
  if (!dropColForm.value.columns.length) {
    ElMessage.warning('请选择要删除的列')
    return
  }
  try {
    await ElMessageBox.confirm(`确定要删除 ${dropColForm.value.columns.length} 列吗？此操作不可撤销。`, '确认')
    loading.value.dropCol = true
    const { data } = await api.cleanDropColumns({ columns: dropColForm.value.columns })
    handleResult(data)
    dropColForm.value.columns = []
  } catch (e) { if (e !== 'cancel') handleError(e) } finally { loading.value.dropCol = false }
}

function addRenameItem() {
  renameForm.value.items.push({ from: '', to: '' })
}

async function runRename() {
  const valid = renameForm.value.items.filter(i => i.from && i.to)
  if (!valid.length) {
    ElMessage.warning('请设置有效的重命名映射')
    return
  }
  loading.value.rename = true
  try {
    const mapping = {}
    valid.forEach(i => { mapping[i.from] = i.to })
    const { data } = await api.cleanRenameColumns({ mapping })
    handleResult(data)
    renameForm.value.items = []
  } catch (e) { handleError(e) } finally { loading.value.rename = false }
}
</script>

<style scoped>
.cleaning-container { height: 100%; overflow-y: auto; }
.cleaning-content { display: flex; flex-direction: column; gap: 12px; }
.section-card { margin-bottom: 0; }
.section-card :deep(.el-card__header) { padding: 10px 16px; background: #fafafa; }
.ai-card :deep(.el-card__header) { background: linear-gradient(135deg, #f0f9ff 0%, #e8f4fd 100%); }
.section-title { font-size: 14px; font-weight: 600; color: #303133; }
.section-header-row { display: flex; justify-content: space-between; align-items: center; }
.quick-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.rename-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.rename-arrow { font-size: 16px; color: #909399; }
.empty-hint { padding: 8px 0; }
.empty { display: flex; align-items: center; justify-content: center; height: 400px; }

.ai-hint { padding: 4px 0; }
.recommend-list { display: flex; flex-direction: column; gap: 8px; }
.recommend-item {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 8px 12px; background: #f8f9fa; border-radius: 6px; border: 1px solid #e8e8e8;
}
.recommend-content { flex: 1; }
.recommend-label { font-size: 13px; font-weight: 600; color: #303133; }
.recommend-reason { font-size: 12px; color: #606266; margin-top: 2px; }

.nl-input-row { display: flex; gap: 8px; align-items: flex-start; }
.nl-input-row .el-input { flex: 1; }
</style>
