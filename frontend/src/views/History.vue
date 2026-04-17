<template>
  <div class="history-page">
    <main class="main-content-inner">
      <div class="card glass trend-card">
        <div class="card-header">
          <div>
            <h3 class="card-title">报警历史</h3>
            <p class="card-subtitle">支持按时间、区域、叉车 ID 组合查询</p>
          </div>
          <span class="card-meta">{{ total }} 条记录</span>
        </div>

        <form class="filter-grid" @submit.prevent="applyFilters">
          <label class="field">
            <span>开始时间</span>
            <input v-model="filters.start_time" type="datetime-local" />
          </label>
          <label class="field">
            <span>结束时间</span>
            <input v-model="filters.end_time" type="datetime-local" />
          </label>
          <label class="field">
            <span>报警区域</span>
            <select v-model="filters.zone">
              <option value="">全部区域</option>
              <option v-for="zone in zoneOptions" :key="zone" :value="zone">{{ zone }}</option>
            </select>
          </label>
          <label class="field">
            <span>叉车 ID</span>
            <select v-model="filters.device_id">
              <option value="">全部设备</option>
              <option v-for="deviceId in deviceOptions" :key="deviceId" :value="deviceId">{{ deviceId }}</option>
            </select>
          </label>
          <label class="field field-page-size">
            <span>每页条数</span>
            <select v-model.number="pageSize">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
            </select>
          </label>
          <div class="filter-actions">
            <button type="submit" class="primary-btn" :disabled="loading">查询</button>
            <button type="button" class="ghost-btn" :disabled="loading" @click="resetFilters">重置</button>
            <button type="button" class="ghost-btn" :disabled="loading" @click="fetchHistory(page)">刷新</button>
          </div>
        </form>

        <div class="table-toolbar">
          <span v-if="loading" class="status-text">正在加载历史记录...</span>
          <span v-else-if="errorMessage" class="status-text error">{{ errorMessage }}</span>
          <span v-else class="status-text">第 {{ page }} / {{ totalPages || 1 }} 页</span>
        </div>

        <div class="table-wrap">
          <table class="history-table">
            <thead>
              <tr>
                <th>设备ID</th>
                <th>报警区域</th>
                <th>报警时间</th>
                <th>风险说明</th>
                <th>AI分析</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!loading && historyData.length === 0">
                <td colspan="6" class="empty-state">当前筛选条件下暂无报警历史</td>
              </tr>
              <tr v-for="(item, index) in historyData" :key="item.id || `${item.device_id}-${item.timestamp}-${index}`">
                <td class="device-id">{{ item.device_id || '-' }}</td>
                <td>{{ item.zone || '未知' }}</td>
                <td class="time-col">{{ formatFullTime(item.timestamp) }}</td>
                <td class="risk-col">{{ getRiskSummary(item) }}</td>
                <td class="analysis-col">{{ getAnalysisText(item) }}</td>
                <td>
                  <button class="view-btn" type="button" @click="showDetail(item)">查看详情</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination">
          <button class="ghost-btn" type="button" :disabled="loading || page <= 1" @click="fetchHistory(page - 1)">上一页</button>
          <span class="page-indicator">共 {{ total }} 条，当前 {{ page }} / {{ totalPages || 1 }}</span>
          <button class="ghost-btn" type="button" :disabled="loading || page >= totalPages" @click="fetchHistory(page + 1)">下一页</button>
        </div>
      </div>
    </main>

    <div class="modal glass-modal" v-if="showDetailModal" @click.self="closeModal">
      <div class="modal-content glass image-modal-content">
        <div class="modal-header">
          <h3>告警详情 - {{ selectedHistory?.device_id || '-' }}</h3>
          <button @click="closeModal" class="modal-close" aria-label="关闭">×</button>
        </div>
        <div class="modal-body">
          <div class="image-slot">
            <img
              v-if="selectedHistory?.image_path"
              :src="'/' + selectedHistory.image_path"
              class="alarm-full-image"
              alt="报警图片"
            />
            <div v-else class="empty-state compact">暂无照片</div>
          </div>

          <div v-if="selectedHistory" class="detail-panel">
            <div class="detail-grid">
              <div>
                <span class="detail-label">设备ID</span>
                <strong>{{ selectedHistory.device_id || '-' }}</strong>
              </div>
              <div>
                <span class="detail-label">报警区域</span>
                <strong>{{ selectedHistory.zone || '未知' }}</strong>
              </div>
              <div>
                <span class="detail-label">事件时间</span>
                <strong>{{ formatFullTime(selectedHistory.timestamp) }}</strong>
              </div>
              <div>
                <span class="detail-label">告警级别</span>
                <strong>{{ getRiskLevel(selectedHistory) }}</strong>
              </div>
            </div>

            <div class="detail-section">
              <span class="detail-label">风险说明</span>
              <p>{{ getRiskSummary(selectedHistory) }}</p>
            </div>

            <div class="detail-section">
              <span class="detail-label">AI 分析</span>
              <p>{{ getAnalysisText(selectedHistory) }}</p>
            </div>

            <div class="detail-section">
              <span class="detail-label">操作入口</span>
              <div class="action-row">
                <button type="button" class="action-btn" @click="setActionFeedback('已标记为待复核，后续可接真实工单流。')">标记待复核</button>
                <button type="button" class="action-btn" @click="setActionFeedback('已生成通知入口占位，后续可接企业微信或短信。')">通知班组</button>
                <button type="button" class="action-btn" @click="setActionFeedback('已预留导出处置单入口，当前为 UI 占位按钮。')">导出处置单</button>
              </div>
              <p v-if="actionFeedback" class="action-feedback">{{ actionFeedback }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../lib/api'

const historyData = ref([])
const showDetailModal = ref(false)
const selectedHistory = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const actionFeedback = ref('')

const page = ref(1)
const total = ref(0)
const totalPages = ref(0)
const pageSize = ref(20)
const deviceOptions = ref([])
const zoneOptions = ref(['A区', 'B区', 'C区', 'D区'])

const filters = ref({
  start_time: '',
  end_time: '',
  zone: '',
  device_id: '',
})

async function fetchHistory(targetPage = 1) {
  loading.value = true
  errorMessage.value = ''
  try {
    const params = {
      page: targetPage,
      page_size: pageSize.value,
    }
    if (filters.value.start_time) params.start_time = filters.value.start_time
    if (filters.value.end_time) params.end_time = filters.value.end_time
    if (filters.value.zone) params.zone = filters.value.zone
    if (filters.value.device_id) params.device_id = filters.value.device_id

    const res = await api.get('/api/history', { params })
    historyData.value = res.data.items || []
    page.value = res.data.page || targetPage
    total.value = res.data.total || 0
    totalPages.value = res.data.total_pages || 0
    deviceOptions.value = res.data.options?.device_ids || []
    zoneOptions.value = res.data.options?.zones || zoneOptions.value
  } catch (error) {
    console.error('历史数据加载失败', error)
    errorMessage.value = error.response?.data?.detail || '历史数据加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  fetchHistory(1)
}

function resetFilters() {
  filters.value = {
    start_time: '',
    end_time: '',
    zone: '',
    device_id: '',
  }
  pageSize.value = 20
  fetchHistory(1)
}

function getAnalysisText(item) {
  if (!item) return '-'
  if (item.description) return item.description
  if (item.description_status === 'pending') return 'AI 分析中'
  if (item.description_status === 'failed') return 'AI 分析失败'
  return '暂无分析结果'
}

function getRiskLevel(item) {
  if (!item) return '待评估'
  if (item.zone === 'B区' || item.zone === 'D区') return '高风险'
  return '中风险'
}

function getRiskSummary(item) {
  if (!item) return '-'
  const zoneText = item.zone || '未知区域'
  return `${zoneText}发生人车接近告警，建议优先核查通行视线、人员驻留和叉车减速执行情况。`
}

function formatFullTime(value) {
  if (!value) return '-'
  return value.replace('T', ' ')
}

function showDetail(item) {
  selectedHistory.value = item
  showDetailModal.value = true
  actionFeedback.value = ''
}

function closeModal() {
  showDetailModal.value = false
  actionFeedback.value = ''
}

function setActionFeedback(message) {
  actionFeedback.value = message
}

onMounted(() => {
  fetchHistory(1)
})
</script>

<style scoped>
.history-page {
  min-height: 100vh;
}

.main-content-inner {
  padding: 28px 32px;
}

.glass {
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow:
    0 8px 32px rgba(140, 120, 180, 0.10),
    inset 0 1px 0 rgba(255, 255, 255, 0.35);
}

.card.trend-card {
  padding: 20px;
  animation: fade-in 0.6s ease;
  border-radius: 24px;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.card-title {
  margin: 0;
  font-family: 'Outfit', sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #3a3550;
}

.card-subtitle {
  margin: 6px 0 0;
  color: #736c90;
  font-size: 13px;
}

.card-meta {
  font-size: 11px;
  color: #8a8aa8;
  background: rgba(255, 255, 255, 0.25);
  padding: 4px 10px;
  border-radius: 999px;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field span {
  font-size: 12px;
  color: #645d7d;
  font-weight: 600;
}

.field input,
.field select {
  height: 42px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid rgba(160, 150, 196, 0.35);
  background: rgba(255, 255, 255, 0.55);
  color: #3a3550;
}

.field-page-size {
  max-width: 120px;
}

.filter-actions {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.primary-btn,
.ghost-btn,
.view-btn,
.action-btn {
  height: 42px;
  padding: 0 16px;
  border-radius: 12px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease;
}

.primary-btn {
  background: linear-gradient(135deg, #ffb26b, #f06b82);
  color: #fff;
}

.ghost-btn {
  background: rgba(184, 169, 232, 0.2);
  color: #4f4a68;
}

.view-btn,
.action-btn {
  background: rgba(240, 160, 160, 0.18);
  color: #9f1f1f;
}

.primary-btn:hover,
.ghost-btn:hover,
.view-btn:hover,
.action-btn:hover {
  transform: translateY(-1px);
}

.primary-btn:disabled,
.ghost-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.table-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}

.status-text {
  font-size: 12px;
  color: #736c90;
}

.status-text.error {
  color: #bb3656;
}

.table-wrap {
  overflow-x: auto;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  overflow: hidden;
}

.history-table th,
.history-table td {
  padding: 12px;
  border-bottom: 1px solid rgba(184, 169, 232, 0.2);
  color: #3a3550;
  vertical-align: top;
}

.history-table th {
  font-weight: 700;
  text-align: left;
  font-size: 13px;
}

.history-table td {
  font-size: 13px;
}

.device-id {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
}

.time-col {
  white-space: nowrap;
  min-width: 180px;
}

.risk-col {
  min-width: 220px;
  color: #705d3f;
  line-height: 1.6;
}

.analysis-col {
  min-width: 220px;
  line-height: 1.6;
  color: #6d6787;
}

.empty-state {
  text-align: center;
  color: #8a8aa8;
  padding: 20px;
}

.empty-state.compact {
  padding: 36px 20px;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
}

.page-indicator {
  font-size: 13px;
  color: #645d7d;
}

.glass-modal {
  position: fixed;
  inset: 0;
  background: rgba(60, 50, 80, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  border-radius: 24px;
  padding: 24px;
  width: min(960px, 92vw);
  max-height: 90vh;
  overflow: auto;
}

.image-modal-content {
  background: rgba(255, 255, 255, 0.9);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #3a3550;
}

.modal-close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  font-size: 20px;
  color: #5c5678;
  cursor: pointer;
}

.modal-body {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(300px, 1fr);
  gap: 18px;
}

.image-slot {
  border-radius: 18px;
  padding: 10px;
  background: rgba(247, 244, 255, 0.8);
}

.alarm-full-image {
  width: 100%;
  max-height: 60vh;
  border-radius: 14px;
  object-fit: contain;
}

.detail-panel {
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.62);
  color: #4f4a68;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.detail-label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: #8b82a5;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.detail-section + .detail-section {
  margin-top: 16px;
}

.detail-section p {
  margin: 0;
  line-height: 1.7;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.action-feedback {
  margin-top: 10px;
  color: #6b6287;
  font-size: 13px;
}

@media (max-width: 1100px) {
  .filter-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .main-content-inner {
    padding: 16px;
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    flex-wrap: wrap;
  }

  .modal-body {
    grid-template-columns: 1fr;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .pagination {
    flex-direction: column;
  }
}
</style>
