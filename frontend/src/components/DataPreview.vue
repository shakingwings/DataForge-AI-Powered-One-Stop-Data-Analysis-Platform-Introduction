<template>
  <div class="preview-container">
    <div v-if="!store.hasData" class="empty">
      <el-empty description="请先上传数据文件" />
    </div>
    <div v-else>
      <div class="toolbar">
        <div class="toolbar-left">
          <span class="data-info">
            共 <b>{{ totalRows }}</b> 行 · <b>{{ columns.length }}</b> 列
          </span>
        </div>
        <div class="toolbar-right">
          <el-button size="small" @click="refresh">刷新</el-button>
          <el-button size="small" type="success" @click="exportExcel">导出Excel</el-button>
        </div>
      </div>
      <el-table
        :data="tableData"
        border stripe size="small"
        max-height="calc(100vh - 310px)"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column type="index" :label="'#'" width="70">
          <template #default="{ $index }">
            {{ (currentPage - 1) * pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column
          v-for="col in columns"
          :key="col"
          :prop="col"
          :label="col"
          min-width="120"
          sortable
          show-overflow-tooltip
        />
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200, 500]"
          :total="totalRows"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="fetchPage"
          @size-change="fetchPage"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../stores/app'
import { getPageData, exportData } from '../api'

const store = useAppStore()
const tableData = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(50)
const totalRows = ref(0)

const columns = computed(() => store.dataInfo?.column_names || [])

async function fetchPage() {
  loading.value = true
  try {
    const { data } = await getPageData(currentPage.value, pageSize.value)
    tableData.value = data.data
    totalRows.value = data.total
    store.previewData = data.data
  } catch (e) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await fetchPage()
}

async function exportExcel() {
  try {
    const resp = await exportData({ format: 'xlsx' })
    const url = URL.createObjectURL(new Blob([resp.data]))
    const a = document.createElement('a')
    a.href = url; a.download = 'data_export.xlsx'; a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

// When dataInfo changes (new upload), reset to page 1
watch(() => store.dataInfo, (val) => {
  if (val) {
    currentPage.value = 1
    totalRows.value = val.rows || 0
    fetchPage()
  }
}, { immediate: true })
</script>

<style scoped>
.preview-container { height: 100%; display: flex; flex-direction: column; }
.toolbar {
  margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;
}
.toolbar-left { display: flex; align-items: center; gap: 12px; }
.toolbar-right { display: flex; gap: 8px; }
.data-info { font-size: 13px; color: #606266; }
.data-info b { color: #409eff; }
.pagination-wrap {
  display: flex; justify-content: flex-end;
  padding: 12px 0; border-top: 1px solid #eee; margin-top: 8px;
}
.empty { display: flex; align-items: center; justify-content: center; height: 400px; }
</style>
