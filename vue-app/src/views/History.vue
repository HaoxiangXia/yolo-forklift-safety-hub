<template>
  <div class="history-page">
    <main class="main-content-inner">
      <div class="card glass trend-card">
        <div class="card-header">
          <h3 class="card-title">报警历史</h3>
          <span class="card-meta">{{ historyData.length }} 条记录</span>
        </div>

        <div class="controls">
          <button @click="fetchHistory">刷新</button>
        </div>

        <div class="table-wrap">
          <table class="history-table">
            <thead>
              <tr>
                <th>设备ID</th>
                <th>报警区域</th>
                <th>报警时间</th>
                <th>AI分析</th>
                <th>照片</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="historyData.length === 0">
                <td colspan="5" class="empty-state">暂无报警历史</td>
              </tr>
              <tr v-for="(item, index) in historyData" :key="item.id || `${item.device_id}-${item.timestamp}-${index}`">
                <td class="device-id">{{ item.device_id || '-' }}</td>
                <td>{{ item.zone || '未知' }}</td>
                <td class="time-col">{{ item.timestamp || '-' }}</td>
                <td class="analysis-col">{{ getAnalysisText(item) }}</td>
                <td>
                  <button
                    v-if="item.image_path"
                    class="view-btn"
                    type="button"
                    @click="showPhoto(item)"
                  >
                    查看照片
                  </button>
                  <span v-else class="no-photo">无照片</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>

    <div class="modal glass-modal" v-if="showImageModal" @click.self="showImageModal = false">
      <div class="modal-content glass image-modal-content">
        <div class="modal-header">
          <h3>报警照片 - {{ selectedHistory?.device_id || '-' }}</h3>
          <button @click="showImageModal = false" class="modal-close" aria-label="关闭">×</button>
        </div>
        <div class="modal-body">
          <img
            v-if="selectedHistory?.image_path"
            :src="'/' + selectedHistory.image_path"
            class="alarm-full-image"
            alt="报警图片"
          />
          <div v-else class="empty-state">暂无照片</div>
          <div v-if="selectedHistory" class="detail-panel">
            <div><strong>设备ID：</strong>{{ selectedHistory.device_id || '-' }}</div>
            <div><strong>报警区域：</strong>{{ selectedHistory.zone || '未知' }}</div>
            <div><strong>报警时间：</strong>{{ selectedHistory.timestamp || '-' }}</div>
            <div><strong>AI分析：</strong>{{ getAnalysisText(selectedHistory) }}</div>
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
const showImageModal = ref(false)
const selectedHistory = ref(null)

async function fetchHistory() {
  try {
    const res = await api.get('/api/history', { params: { limit: 50 } })
    historyData.value = res.data.items || []
  } catch (e) {
    console.error('历史数据加载失败', e)
  }
}

function getAnalysisText(item) {
  if (!item) return '-'
  if (item.description) return item.description
  if (item.description_status === 'pending') return 'AI 分析中'
  if (item.description_status === 'failed') return 'AI 分析失败'
  return '-'
}

function showPhoto(item) {
  selectedHistory.value = item
  showImageModal.value = true
}

onMounted(fetchHistory)
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
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.card-title {
  font-family: 'Outfit', sans-serif;
  font-size: 15px;
  font-weight: 600;
  color: #3a3550;
}

.card-meta {
  font-size: 11px;
  color: #8a8aa8;
  background: rgba(255, 255, 255, 0.25);
  padding: 4px 10px;
  border-radius: 999px;
}

.controls {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.controls button {
  padding: 6px 12px;
  border-radius: 10px;
  border: none;
  background: rgba(184,169,232,0.2);
  color: #3a3550;
  cursor: pointer;
  transition: all 0.2s;
}

.controls button:hover {
  background: rgba(184,169,232,0.35);
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
  border-bottom: 1px solid rgba(184,169,232,0.2);
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
  min-width: 160px;
}

.analysis-col {
  min-width: 220px;
  line-height: 1.5;
  color: #6d6787;
}

.view-btn {
  padding: 6px 12px;
  border-radius: 10px;
  border: none;
  background: rgba(240, 160, 160, 0.22);
  color: #9f1f1f;
  font-weight: 600;
  cursor: pointer;
}

.view-btn:hover {
  background: rgba(240, 160, 160, 0.34);
}

.no-photo {
  color: #8a8aa8;
}

.empty-state {
  text-align: center;
  color: #8a8aa8;
  padding: 20px;
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
  width: min(860px, 92vw);
  max-height: 90vh;
  overflow: auto;
}

.image-modal-content {
  background: rgba(255, 255, 255, 0.85);
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
  background: rgba(255,255,255,0.5);
  font-size: 20px;
  color: #5c5678;
  cursor: pointer;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.alarm-full-image {
  max-width: 100%;
  max-height: 60vh;
  border-radius: 14px;
  object-fit: contain;
}

.detail-panel {
  padding: 16px 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.56);
  color: #4f4a68;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .main-content-inner {
    padding: 16px;
  }
}
</style>
