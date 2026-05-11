import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({ baseURL: '/api', timeout: 120000 })

// Response interceptor - global error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg = error.response?.data?.error
      || error.response?.data?.detail
      || error.message
      || '网络请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

// Data
export const uploadData = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/data/upload', form)
}
export const getDataInfo = () => api.get('/data/info')
export const getPreview = (rows = 20) => api.get('/data/preview', { params: { rows } })
export const getPageData = (page = 1, pageSize = 50) =>
  api.get('/data/page', { params: { page, page_size: pageSize } })
export const clearData = () => api.delete('/data/clear')

// Chat
export const sendMessage = (message, sessionId = 'default') =>
  api.post('/chat', { message, session_id: sessionId })

export const chatStream = (message, sessionId = 'default') =>
  fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  })

// Analysis & Visualization
export const runAnalysis = (data) => api.post('/analysis/run', data)
export const generateChart = (data) => api.post('/visualization/generate', data)
export const getMapData = (type = 'china') => api.get('/visualization/map-data', { params: { type } })
export const autoCharts = () => api.get('/visualization/auto')

// Export
export const exportData = (data) => api.post('/export/data', data, { responseType: 'blob' })
export const exportChart = (data) => api.post('/export/chart', data, { responseType: 'blob' })
export const exportReport = (data) => api.post('/export/report', data, { responseType: 'blob' })

// Config
export const getConfig = () => api.get('/config')
export const updateConfig = (data) => api.post('/config', data)

// Cleaning
export const cleanAuto = () => api.post('/cleaning/auto')
export const cleanFillMissing = (data) => api.post('/cleaning/fill-missing', data)
export const cleanFillValue = (data) => api.post('/cleaning/fill-value', data)
export const cleanFillForward = (data) => api.post('/cleaning/fill-forward', data)
export const cleanFillBackward = (data) => api.post('/cleaning/fill-backward', data)
export const cleanDropDuplicates = () => api.post('/cleaning/drop-duplicates')
export const cleanDeduplicateSubset = (data) => api.post('/cleaning/deduplicate-subset', data)
export const cleanRemoveOutliers = (data) => api.post('/cleaning/remove-outliers', data)
export const cleanTrim = () => api.post('/cleaning/trim-whitespace')
export const cleanStandardizeCase = (data) => api.post('/cleaning/standardize-case', data)
export const cleanRenameColumns = (data) => api.post('/cleaning/rename-columns', data)
export const cleanDropColumns = (data) => api.post('/cleaning/drop-columns', data)
export const cleanDropRows = (data) => api.post('/cleaning/drop-rows', data)
export const cleanConvert = (data) => api.post('/cleaning/convert-dtype', data)
export const cleanTruncateDatetime = (data) => api.post('/cleaning/truncate-datetime', data)
export const cleanRecommend = () => api.post('/cleaning/recommend')
export const cleanExecuteSteps = (data) => api.post('/cleaning/execute-steps', data)
export const cleanAiClean = (data) => api.post('/cleaning/ai-clean', data)
export const cleanAiTransform = (data) => api.post('/cleaning/ai-transform', data)

// History
export const getSessions = () => api.get('/history/sessions')
export const getSessionDetail = (id) => api.get(`/history/sessions/${id}`)
export const deleteSession = (id) => api.delete(`/history/sessions/${id}`)
