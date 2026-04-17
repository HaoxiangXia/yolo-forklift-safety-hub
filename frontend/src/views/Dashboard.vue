<template>
  <div class="dashboard">
    <main class="main-content">
      <div class="dashboard-grid">
        <!-- Center: Map + Chart -->
        <div class="center-section">
          <div class="card glass map-card">
            <div class="kpi-section">
              <div class="kpi-item">
                <span class="kpi-label">设备总数</span>
                <span class="kpi-value kpi-total">{{ totalDevices }}</span>
              </div>
              <div class="kpi-item">
                <span class="kpi-label">在线</span>
                <span class="kpi-value kpi-online">{{ onlineDevices }}</span>
              </div>
              <div class="kpi-item">
                <span class="kpi-label">报警</span>
                <span class="kpi-value kpi-alarm">{{ alarmDevices }}</span>
              </div>
            </div>
            <div class="map-content">
              <div class="card-header">
                <h3 class="card-title">工厂平面图</h3>
                <span class="card-meta">{{ mapMeta }}</span>
              </div>
              <div class="map-stage">
                <img
                  :src="DASHBOARD_MAP_URL"
                  alt="工厂平面图"
                  class="map-background-image"
                />
                <div ref="mapChart" class="map-container"></div>
              </div>
              <div class="map-legend">
                <span class="legend-item"><span class="legend-dot normal"></span>正常</span>
                <span class="legend-item"><span class="legend-dot alarm"></span>报警</span>
                <span class="legend-item"><span class="legend-dot offline"></span>离线</span>
              </div>
            </div>
          </div>

          <div class="card glass chart-card">
            <div class="card-header">
              <h3 class="card-title">报警次数趋势</h3>
              <span class="card-tag">24小时</span>
            </div>
            <LineChart :series="chartSeries" :labels="chartLabels" :height="'180px'" :enable-data-zoom="false" />
          </div>
        </div>

        <!-- Right: Alarm List -->
        <div class="card glass alarm-card">
          <div class="card-header">
            <h3 class="card-title">告警事件</h3>
            <span class="card-meta">{{ alarmList.length }} 条</span>
          </div>
          <div class="alarm-list">
            <div 
              v-for="(alarm, index) in alarmList" 
              :key="alarm.device_id + alarm.timestamp"
              class="alarm-item"
              :style="{ animationDelay: `${index * 0.05}s` }"
              @click="showAlarmImage(alarm)"
            >
              <div class="alarm-item-header">
                <span class="alarm-status-dot" :class="{ active: isRecentAlarm(alarm) }"></span>
                <span class="alarm-device">{{ alarm.device_id }}</span>
                <span class="alarm-time">{{ formatAlarmTime(alarm.timestamp) }}</span>
              </div>
              <div class="alarm-summary">
                <span class="alarm-result-badge" :class="getAlarmResultClass(alarm)">
                  {{ getAlarmResultText(alarm) }}
                </span>
                <span class="alarm-reason">{{ getAlarmReason(alarm) }}</span>
              </div>
              <div class="alarm-item-body">
                <span class="alarm-zone" v-if="alarm.zone">{{ alarm.zone }}</span>
                <img v-if="alarm.image_path" :src="'/' + alarm.image_path" class="alarm-thumb" alt="报警图片" @error="handleImageError" />
                <span v-if="!alarm.image_path" class="alarm-no-image">无图片</span>
                <span class="alarm-duration">{{ getAlarmDuration(alarm) }}</span>
              </div>
              <p class="alarm-analysis" :class="{ pending: isAnalysisPending(alarm), failed: isAnalysisFailed(alarm) }">
                {{ getAnalysisText(alarm) }}
              </p>
            </div>
            <div v-if="alarmList.length === 0" class="alarm-empty">
              <span class="empty-icon">&#10003;</span>
              <span>暂无告警记录</span>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Image Modal -->
    <div class="modal glass-modal" v-if="showImageModal" @click.self="showImageModal = false">
      <div class="modal-content glass image-modal-content">
        <div class="modal-header">
          <h3>告警图片 - {{ selectedAlarm?.device_id }}</h3>
          <button @click="showImageModal = false" class="modal-close" aria-label="关闭">&times;</button>
        </div>
        <div class="modal-body image-modal-body">
          <img v-if="selectedAlarm?.image_path" :src="'/' + selectedAlarm.image_path" class="alarm-full-image" alt="告警图片" />
          <div v-else class="no-image">暂无图片</div>
          <div class="alarm-detail-panel" v-if="selectedAlarm">
            <div class="alarm-detail-row">
              <span class="detail-label">事件时间</span>
              <span class="detail-value">{{ formatAbsoluteTime(selectedAlarm.timestamp) }}</span>
            </div>
            <div class="alarm-detail-row">
              <span class="detail-label">报警结果</span>
              <span class="detail-value">
                <span class="alarm-result-badge" :class="getAlarmResultClass(selectedAlarm)">
                  {{ getAlarmResultText(selectedAlarm) }}
                </span>
              </span>
            </div>
            <div class="alarm-detail-row">
              <span class="detail-label">报警原因</span>
              <span class="detail-value">{{ getAlarmReason(selectedAlarm) }}</span>
            </div>
            <div class="alarm-detail-row is-block">
              <span class="detail-label">风险说明</span>
              <p class="detail-analysis">{{ getRiskDescription(selectedAlarm) }}</p>
            </div>
            <div class="alarm-detail-row">
              <span class="detail-label">AI分析</span>
              <p class="detail-analysis" :class="{ pending: isAnalysisPending(selectedAlarm), failed: isAnalysisFailed(selectedAlarm) }">
                {{ getAnalysisText(selectedAlarm) }}
              </p>
            </div>
            <div class="alarm-detail-row is-block">
              <span class="detail-label">操作入口</span>
              <div class="detail-actions">
                <button type="button" class="detail-action-btn" @click="triggerAlarmAction('已标记为待跟进，后续可接真实处置流。')">标记已跟进</button>
                <button type="button" class="detail-action-btn" @click="triggerAlarmAction('已预留通知入口，后续可接短信或企业微信。')">通知负责人</button>
                <button type="button" class="detail-action-btn" @click="triggerAlarmAction('已预留复盘入口，当前先作为 UI 占位按钮。')">发起复盘</button>
              </div>
              <p v-if="alarmActionFeedback" class="detail-action-feedback">{{ alarmActionFeedback }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { io } from 'socket.io-client'
import api from '../lib/api'
import { getAuthToken } from '../lib/auth'
import LineChart from '../components/LineChart.vue'

const mapChart = ref(null)
const devices = ref([])
const alarmList = ref([])
const mapMeta = ref('数据加载中...')

const totalDevices = computed(() => devices.value.length)
const onlineDevices = computed(() => devices.value.filter(d => d.online_status === 1).length)
const alarmDevices = computed(() => devices.value.filter(d => d.online_status === 1 && d.alarm_status === 1).length)

const chartLabels = ref(Array.from({ length: 24 }, (_, i) => `${i}:00`))
const chartSeries = ref([])

const showImageModal = ref(false)
const selectedAlarm = ref(null)
const alarmActionFeedback = ref('')
const DASHBOARD_MAP_URL = '/Dashboard.png'

let mapChartInstance = null
const MAP_COORD_WIDTH = 1920
const MAP_COORD_HEIGHT = 1080
const MAP_MARKER_OUTER_SIZE = 42
const MAP_MARKER_MIDDLE_SIZE = 32
const MAP_MARKER_INNER_SIZE = 22

const C = {
  text: '#5c5678',
  textSec: '#9890b0',
  purple: '#b8a9e8',
  green: '#a8e6cf',
  red: '#f0a0a0',
  offline: '#b0a8c8',
}

async function fetchAlarmTrend() {
  try {
    const res = await api.get('/api/dashboard/alarm-trend')
    const data = res.data || {}
    const labels = Array.isArray(data.labels)
      ? data.labels
      : Array.from({ length: 24 }, (_, i) => `${i}:00`)
    const today = Array.isArray(data.today_counts) ? data.today_counts : []
    const yesterday = Array.isArray(data.yesterday_counts) ? data.yesterday_counts : []

    chartLabels.value = labels
    chartSeries.value = [
      {
        name: '今日',
        data: today,
        color: C.purple,
        areaColor: ['rgba(184,169,232,0.18)', 'rgba(184,169,232,0.02)'],
        lineWidth: 3,
      },
      {
        name: '昨日',
        data: yesterday,
        color: C.green,
        areaColor: ['rgba(208,245,120,0.16)', 'rgba(208,245,120,0.02)'],
        lineWidth: 3,
      },
    ]
  } catch (e) {
    console.error('报警趋势数据加载失败', e)
  }
}

function buildMapPointData() {
  return devices.value.map(dev => {
    let color = C.offline
    let statusText = '离线'
    if (dev.online_status === 1) {
      if (dev.alarm_status === 1) {
        color = C.red
        statusText = '报警'
      } else {
        color = C.green
        statusText = '正常'
      }
    }
    return {
      name: dev.device_id,
      value: [dev.pos_x || 0, dev.pos_y || 0],
      itemStyle: { color },
      statusText,
      lastSeen: dev.last_seen || '-',
    }
  })
}

function updateMap() {
  if (!mapChartInstance) return
  updateMapLayout()

  const pointData = buildMapPointData()

  mapChartInstance.setOption({
    series: [
      { data: pointData },
      { data: pointData },
      { data: pointData },
    ],
  })

  const now = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  mapMeta.value = `最近更新 ${now}`
}

function updateMapLayout() {
  if (!mapChartInstance) return

  const chartWidth = mapChartInstance.getWidth()
  const chartHeight = mapChartInstance.getHeight()
  if (!chartWidth || !chartHeight) return

  const scale = Math.min(
    chartWidth / MAP_COORD_WIDTH,
    chartHeight / MAP_COORD_HEIGHT
  )
  const fittedWidth = Math.round(MAP_COORD_WIDTH * scale)
  const fittedHeight = Math.round(MAP_COORD_HEIGHT * scale)
  const offsetLeft = Math.round((chartWidth - fittedWidth) / 2)
  const offsetTop = Math.round((chartHeight - fittedHeight) / 2)

  mapChartInstance.setOption({
    grid: {
      left: offsetLeft,
      top: offsetTop,
      width: fittedWidth,
      height: fittedHeight,
      containLabel: false,
    },
    xAxis: {
      min: 0,
      max: MAP_COORD_WIDTH,
      show: false,
    },
    yAxis: {
      min: 0,
      max: MAP_COORD_HEIGHT,
      inverse: true,
      show: false,
    },
  })
}

async function initData() {
  try {
    const [devicesRes, alarmsRes] = await Promise.all([
      api.get('/api/devices'),
      api.get('/api/recent-alarms?limit=10')
    ])
    devices.value = devicesRes.data.devices || []
    alarmList.value = alarmsRes.data.alarms || []
    updateMap()
  } catch (e) {
    console.error('初始化数据失败:', e)
  }
}

function isRecentAlarm(alarm) {
  if (!alarm.timestamp) return false
  const alarmTime = new Date(alarm.timestamp)
  const now = new Date()
  const diffMinutes = (now - alarmTime) / (1000 * 60)
  return diffMinutes < 30
}

function formatAlarmTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays}天前`
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function getAlarmDuration(alarm) {
  if (!alarm.timestamp) return ''
  const alarmTime = new Date(alarm.timestamp)
  const now = new Date()
  const diffMs = now - alarmTime
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return '刚触发'
  if (diffMins < 60) return `持续 ${diffMins} 分钟`
  const hours = Math.floor(diffMins / 60)
  const mins = diffMins % 60
  return `持续 ${hours}小时${mins}分`
}

function getAlarmResultText(alarm) {
  return alarm?.alarm === 1 ? '已报警' : '已恢复'
}

function getAlarmResultClass(alarm) {
  return alarm?.alarm === 1 ? 'is-alarm' : 'is-normal'
}

function getAlarmReason(_alarm) {
  return '人离叉车过近'
}

function getRiskDescription(alarm) {
  if (!alarm) return '暂无风险说明'
  const zone = alarm.zone || '未知区域'
  return `${zone}出现人车距离过近告警，建议优先核查现场视线遮挡、人员停留和叉车减速执行情况。`
}

function isAnalysisPending(alarm) {
  return alarm?.description_status === 'pending'
}

function isAnalysisFailed(alarm) {
  return alarm?.description_status === 'failed'
}

function getAnalysisText(alarm) {
  if (!alarm) return '暂无分析'
  if (alarm.description) return alarm.description
  if (isAnalysisPending(alarm)) return 'AI 正在分析报警图片...'
  if (isAnalysisFailed(alarm)) return 'AI 分析失败，请稍后重试'
  return 'AI 分析结果暂未生成'
}

function formatAbsoluteTime(timestamp) {
  if (!timestamp) return '-'
  return timestamp.replace('T', ' ')
}

function handleImageError(e) {
  e.target.style.display = 'none'
}

function showAlarmImage(alarm) {
  selectedAlarm.value = alarm
  showImageModal.value = true
  alarmActionFeedback.value = ''
}

function triggerAlarmAction(message) {
  alarmActionFeedback.value = message
}

let socket = null
let trendTimer = null

onMounted(() => {
  mapChartInstance = echarts.init(mapChart.value)
  mapChartInstance.setOption({
    backgroundColor: 'transparent',
    grid: {
      left: 0,
      top: 0,
      width: '100%',
      height: '100%',
      containLabel: false,
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.85)',
      borderColor: 'rgba(255,255,255,0.3)',
      borderWidth: 1,
      textStyle: { color: C.text, fontSize: 12 },
      formatter: p => `<strong>${p.data.name}</strong><br/>状态: ${p.data.statusText}<br/>最后更新: ${p.data.lastSeen}`,
    },
    xAxis: {
      type: 'value',
      min: 0,
      max: MAP_COORD_WIDTH,
      show: false,
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: MAP_COORD_HEIGHT,
      inverse: true,
      show: false,
    },
    series: [{
      type: 'scatter',
      coordinateSystem: 'cartesian2d',
      clip: true,
      silent: true,
      z: 1,
      symbolSize: MAP_MARKER_OUTER_SIZE,
      itemStyle: {
        color: '#111111',
        opacity: 0.96,
      },
      data: [],
    }, {
      type: 'scatter',
      coordinateSystem: 'cartesian2d',
      clip: true,
      silent: true,
      z: 2,
      symbolSize: MAP_MARKER_MIDDLE_SIZE,
      itemStyle: {
        color: 'rgba(255, 255, 255, 0.96)',
      },
      data: [],
    }, {
      type: 'scatter',
      coordinateSystem: 'cartesian2d',
      clip: true,
      z: 3,
      symbolSize: MAP_MARKER_INNER_SIZE,
      data: [],
    }],
  })
  nextTick(() => {
    requestAnimationFrame(() => {
      mapChartInstance?.resize()
      updateMapLayout()
      updateMap()
    })
  })

  fetchAlarmTrend()
  initData()

  socket = io({ auth: { token: getAuthToken() } })
  socket.on('device_update', () => {
    initData()
    fetchAlarmTrend()
  })

  trendTimer = setInterval(() => {
    fetchAlarmTrend()
  }, 60000)

  const resizeHandler = () => {
    mapChartInstance?.resize()
    updateMapLayout()
  }
  window.addEventListener('resize', resizeHandler)

  onUnmounted(() => {
    window.removeEventListener('resize', resizeHandler)
    if (trendTimer) {
      clearInterval(trendTimer)
      trendTimer = null
    }
    mapChartInstance?.dispose()
    socket?.disconnect()
  })
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  position: relative;
  --dashboard-content-padding-y: 56px;
  --dashboard-sidebar-footer-zone: 152px;
}

.main-content {
  padding: 28px 32px;
  overflow-y: auto;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  grid-template-rows: 1fr auto;
  gap: 20px;
  grid-template-areas:
    "center alarm"
    "chart alarm";
  animation: grid-reveal 0.8s cubic-bezier(0.4, 0, 0.2, 1) both;
}

@keyframes grid-reveal {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.glass {
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow:
    0 8px 32px rgba(140, 120, 180, 0.10),
    inset 0 1px 0 rgba(255, 255, 255, 0.35);
  transition: box-shadow 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.card {
  border-radius: 24px;
  padding: 20px;
}

.card:hover {
  box-shadow:
    0 16px 48px rgba(140, 120, 180, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
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
  letter-spacing: 0.01em;
  flex-shrink: 0;
}

.card-meta {
  font-size: 11px;
  color: #8a8aa8;
  background: rgba(255, 255, 255, 0.25);
  padding: 4px 10px;
  border-radius: 999px;
  backdrop-filter: blur(4px);
}

.card-tag {
  font-size: 11px;
  color: #8a8aa8;
  background: rgba(255, 255, 255, 0.25);
  padding: 4px 10px;
  border-radius: 999px;
  backdrop-filter: blur(4px);
}

/* Center Section */
.center-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Map Card: KPI sidebar + map content side by side */
.map-card {
  display: flex;
  flex-direction: row;
  gap: 0;
  padding: 0;
  overflow: hidden;
}

.kpi-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 24px 16px;
  background: rgba(255, 255, 255, 0.10);
  border-right: 1px solid rgba(255, 255, 255, 0.2);
  flex-shrink: 0;
  width: 120px;
  justify-content: center;
  animation: kpi-slide 0.6s cubic-bezier(0.4, 0, 0.2, 1) 0.2s both;
}

@keyframes kpi-slide {
  from { opacity: 0; transform: translateX(-12px); }
  to { opacity: 1; transform: translateX(0); }
}

.kpi-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 18px 8px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.18);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.kpi-item:hover {
  background: rgba(255, 255, 255, 0.20);
  transform: scale(1.03);
}

.kpi-item .kpi-label {
  font-family: 'Outfit', sans-serif;
  font-size: 10px;
  font-weight: 500;
  color: #8a8aa8;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.kpi-item .kpi-value {
  font-family: 'Outfit', sans-serif;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
}

.map-content {
  flex: 1;
  min-width: 0;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.kpi-total {
  color: #b8a9e8;
  text-shadow: 0 0 20px rgba(184, 169, 232, 0.3);
}

.kpi-online {
  color: #a8e6cf;
  text-shadow: 0 0 20px rgba(168, 230, 207, 0.3);
}

.kpi-alarm {
  color: #f0a0a0;
  text-shadow: 0 0 20px rgba(240, 160, 160, 0.3);
  animation: alarmPulse 2.5s ease-in-out infinite;
}

@keyframes alarmPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.03); }
}

.map-stage {
  position: relative;
  width: 100%;
  height: 420px;
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.1)),
    rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 2px 8px rgba(140, 120, 180, 0.06);
  overflow: hidden;
}

.map-background-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
  opacity: 0.92;
  pointer-events: none;
}

.map-container {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.map-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 14px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: #8a8aa8;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: 0 0 6px currentColor;
}

.legend-dot.normal { background: #a8e6cf; color: #a8e6cf; }
.legend-dot.alarm { background: #f0a0a0; color: #f0a0a0; }
.legend-dot.offline { background: #b0a8c8; color: #b0a8c8; }

.chart-card {
  grid-area: chart;
}

/* Alarm List */
.alarm-card {
  grid-area: alarm;
  display: flex;
  flex-direction: column;
  align-self: start;
  height: calc(100vh - var(--dashboard-content-padding-y) - var(--dashboard-sidebar-footer-zone));
  max-height: calc(100vh - var(--dashboard-content-padding-y) - var(--dashboard-sidebar-footer-zone));
}

.alarm-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-right: 4px;
}

.alarm-list::-webkit-scrollbar {
  width: 4px;
}

.alarm-list::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

.alarm-list::-webkit-scrollbar-thumb {
  background: rgba(184, 169, 232, 0.4);
  border-radius: 2px;
}

.alarm-item {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: alarm-slide-in 0.5s cubic-bezier(0.4, 0, 0.2, 1) both;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

@keyframes alarm-slide-in {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.alarm-item:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateX(-4px);
  border-color: rgba(240, 160, 160, 0.3);
}

.alarm-item-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.alarm-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.alarm-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #b0a8c8;
  flex-shrink: 0;
}

.alarm-status-dot.active {
  background: #f0a0a0;
  box-shadow: 0 0 8px rgba(240, 160, 160, 0.6);
  animation: dot-pulse 1.5s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.alarm-device {
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #3a3550;
  flex: 1;
}

.alarm-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #8a8aa8;
}

.alarm-item-body {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.alarm-thumb {
  width: 48px;
  height: 36px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.alarm-zone {
  font-size: 10px;
  font-weight: 600;
  color: #b8a9e8;
  background: rgba(184, 169, 232, 0.15);
  padding: 3px 8px;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.alarm-duration {
  font-size: 11px;
  color: #b8a9e8;
  font-weight: 500;
  margin-left: auto;
}

.alarm-no-image {
  font-size: 11px;
  color: #a0a0b0;
  font-style: italic;
}

.alarm-result-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.alarm-result-badge.is-alarm {
  color: #9f1f1f;
  background: rgba(240, 160, 160, 0.26);
  border: 1px solid rgba(208, 64, 64, 0.18);
}

.alarm-result-badge.is-normal {
  color: #2c7051;
  background: rgba(168, 230, 207, 0.26);
  border: 1px solid rgba(62, 150, 103, 0.18);
}

.alarm-reason {
  font-size: 12px;
  color: #5c5678;
  font-weight: 600;
}

.alarm-analysis {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #6d6787;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.alarm-analysis.pending {
  color: #8a8aa8;
}

.alarm-analysis.failed {
  color: #b55353;
}

.alarm-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #8a8aa8;
  gap: 12px;
}

.empty-icon {
  font-size: 32px;
  color: #a8e6cf;
}

/* Modal */
.glass-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(60, 50, 80, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: modal-fade 0.3s ease;
}

@keyframes modal-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(24px);
  border-radius: 24px;
  padding: 24px;
  max-width: 90vw;
  max-height: 90vh;
  overflow: auto;
  animation: modal-scale 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes modal-scale {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.image-modal-content {
  max-width: 800px;
  width: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.modal-header h3 {
  font-family: 'Outfit', sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #3a3550;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 50%;
  font-size: 20px;
  color: #5c5678;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.modal-close:hover {
  background: rgba(240, 160, 160, 0.4);
  color: #d04040;
}

.modal-body {
  text-align: center;
}

.alarm-full-image {
  max-width: 100%;
  max-height: 70vh;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(140, 120, 180, 0.2);
}

.no-image {
  color: #8a8aa8;
  padding: 40px;
}

.alarm-detail-panel {
  margin-top: 20px;
  padding: 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.56);
  border: 1px solid rgba(255, 255, 255, 0.4);
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.alarm-detail-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alarm-detail-row.is-block {
  padding-top: 4px;
  border-top: 1px solid rgba(184, 169, 232, 0.18);
}

.detail-label {
  font-size: 11px;
  font-weight: 700;
  color: #8a8aa8;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-value {
  font-size: 14px;
  color: #3a3550;
}

.detail-analysis {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #4f4a68;
}

.detail-analysis.pending {
  color: #8a8aa8;
}

.detail-analysis.failed {
  color: #b55353;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.detail-action-btn {
  min-height: 36px;
  padding: 0 14px;
  border: none;
  border-radius: 999px;
  background: rgba(240, 160, 160, 0.18);
  color: #9f1f1f;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease;
}

.detail-action-btn:hover {
  transform: translateY(-1px);
  background: rgba(240, 160, 160, 0.3);
}

.detail-action-feedback {
  margin: 8px 0 0;
  font-size: 13px;
  color: #6d6787;
}

/* Responsive */
@media (max-width: 1200px) {
  .dashboard-grid {
    grid-template-columns: 1fr 280px;
  }

  .map-card {
    flex-direction: column;
  }

  .kpi-section {
    flex-direction: row;
    flex-wrap: wrap;
    width: 100%;
    padding: 16px;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    justify-content: center;
  }

  .kpi-item {
    flex: 1;
    min-width: 80px;
    padding: 12px 6px;
  }

  .kpi-item .kpi-value {
    font-size: 22px;
  }
}

@media (max-width: 768px) {
  .main-content {
    padding: 16px;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
    grid-template-areas:
      "map"
      "alarm"
      "chart";
  }

  .kpi-section {
    flex-direction: column;
  }

  .map-stage {
    height: 280px;
  }

  .alarm-card {
    height: auto;
    max-height: 400px;
  }
}
</style>
