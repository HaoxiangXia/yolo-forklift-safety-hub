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
              <div class="kpi-item kpi-clickable" @click="toggleForkDetail">
                <span class="kpi-label">在线</span>
                <span class="kpi-value kpi-online">{{ onlineDevices }}</span>
                <transition name="fork-detail">
                  <div v-if="showForkDetail" class="fork-detail-popup" @click.stop>
                    <div
                      v-for="fork in onlineForkList"
                      :key="fork.device_id"
                      class="fork-detail-row"
                    >
                      <div class="fork-detail-left">
                        <span class="fork-detail-name">{{ fork.device_id }}</span>
                        <span class="fork-detail-zone">{{ getZoneName(fork.pos_x || 0, fork.pos_y || 0) }}</span>
                      </div>
                      <span class="fork-detail-pos">({{ fork.pos_x?.toFixed(0) }}, {{ fork.pos_y?.toFixed(0) }})</span>
                      <span class="fork-detail-status" :class="{ alarming: fork.alarm_status >= 1 }">
                        {{ fork.alarm_status >= 2 ? '报警' : fork.alarm_status === 1 ? '警告' : '正常' }}
                      </span>
                    </div>
                    <div v-if="onlineForkList.length === 0" class="fork-detail-empty">暂无在线叉车</div>
                  </div>
                </transition>
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
                <span class="legend-item"><span class="legend-fork"></span>叉车</span>
                <span class="legend-item"><span class="legend-person"></span>行人</span>
              </div>
            </div>
          </div>

          <div class="card glass chart-card">
            <div class="card-header">
              <h3 class="card-title">报警次数趋势</h3>
              <span class="card-tag">24小时</span>
            </div>
            <LineChart :series="chartSeries" :labels="chartLabels" :height="'180px'" />
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
            <div class="alarm-detail-row">
              <span class="detail-label">AI分析</span>
              <p class="detail-analysis" :class="{ pending: isAnalysisPending(selectedAlarm), failed: isAnalysisFailed(selectedAlarm) }">
                {{ getAnalysisText(selectedAlarm) }}
              </p>
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

const totalDevices = computed(() => devices.value.filter(d => d.device_id.startsWith('FORK-')).length)
const onlineDevices = computed(() => devices.value.filter(d => d.device_id.startsWith('FORK-') && (d.online_status === 1 || forkMovementData.value[d.device_id])).length)
const alarmDevices = computed(() => devices.value.filter(d => d.device_id.startsWith('FORK-') && (d.online_status === 1 || forkMovementData.value[d.device_id]) && d.alarm_status >= 1).length)
const onlineForkList = computed(() => devices.value.filter(d => d.device_id.startsWith('FORK-') && (d.online_status === 1 || forkMovementData.value[d.device_id])))
const showForkDetail = ref(false)

function toggleForkDetail() {
  showForkDetail.value = !showForkDetail.value
}

const chartLabels = ref(Array.from({ length: 24 }, (_, i) => `${i}:00`))
const chartSeries = ref([])

const showImageModal = ref(false)
const selectedAlarm = ref(null)
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
  warning: '#FFD700',
}

const persons = ref([
  { id: 'P001', name: '行人A', pos_x: 300, pos_y: 300, speed: 1, direction: Math.random() * Math.PI * 2 },
  { id: 'P002', name: '行人B', pos_x: 800, pos_y: 600, speed: 1.2, direction: Math.random() * Math.PI * 2 },
  { id: 'P003', name: '行人C', pos_x: 1200, pos_y: 400, speed: 0.8, direction: Math.random() * Math.PI * 2 },
])

const forkMovementData = ref({
  'FORK-001': {
    path: [
      [630, 760], [630, 150], [150, 150], [150, 760], [630, 760],
    ],
    speed: 1.5,
  },
  'FORK-002': {
    path: [
      [630, 760], [1417, 760], [1417, 950], [630, 950], [630, 760],
    ],
    speed: 1.8,
  },
  'FORK-003': {
    path: [
      [630, 760], [1417, 760], [1417, 150], [630, 150], [630, 760],
    ],
    speed: 2,
  },
})

const forkStates = ref({
  'FORK-001': { x: 630, y: 760, currentPoint: 0, direction: 0 },
  'FORK-002': { x: 630, y: 760, currentPoint: 0, direction: 0 },
  'FORK-003': { x: 630, y: 760, currentPoint: 0, direction: 0 },
})

const FORK_COLOR = '#3498db'
const PERSON_COLOR = '#2ecc71'
const WARNING_INNER_COLOR = 'rgba(255, 0, 0, 0.3)'
const WARNING_OUTER_COLOR = 'rgba(255, 200, 0, 0.3)'
const ALARM_DISTANCE = 60
const WARN_DISTANCE = 100
let coordScale = 0.4

function getZoneName(x, y) {
  if (x < 350) return '大道'
  if (y < 500) {
    if (x < 800) return '收货暂存区'
    return '高位货架区'
  }
  if (y < 850) {
    if (x < 800) return '大道'
    return '散货存放区'
  }
  return '货车装载区'
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
      if (dev.alarm_status >= 2) {
        color = C.red
        statusText = '报警'
      } else if (dev.alarm_status === 1) {
        color = '#f39c12'
        statusText = '警告'
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

function updateForkPositions() {
  const forkIds = Object.keys(forkMovementData.value)

  forkIds.forEach(deviceId => {
    const movement = forkMovementData.value[deviceId]
    const state = forkStates.value[deviceId]
    if (!movement || !state) return

    const path = movement.path
    const nextIdx = (state.currentPoint + 1) % path.length
    const nextPoint = path[nextIdx]

    const dx = nextPoint[0] - state.x
    const dy = nextPoint[1] - state.y
    const distToNext = Math.sqrt(dx * dx + dy * dy)

    if (distToNext < movement.speed) {
      state.x = nextPoint[0]
      state.y = nextPoint[1]
      state.currentPoint = nextIdx
      const afterNextIdx = (nextIdx + 1) % path.length
      const afterNext = path[afterNextIdx]
      state.direction = Math.atan2(afterNext[1] - nextPoint[1], afterNext[0] - nextPoint[0]) * 180 / Math.PI
    } else {
      state.x += (dx / distToNext) * movement.speed
      state.y += (dy / distToNext) * movement.speed
      state.direction = Math.atan2(dy, dx) * 180 / Math.PI
    }
  })

  forkIds.forEach(id => {
    const dev = devices.value.find(d => d.device_id === id)
    const state = forkStates.value[id]
    if (dev && state) {
      dev.pos_x = state.x
      dev.pos_y = state.y
      dev.online_status = 1
      dev.alarm_status = 0
    }
  })

  for (let i = 0; i < forkIds.length; i++) {
    for (let j = i + 1; j < forkIds.length; j++) {
      const si = forkStates.value[forkIds[i]]
      const sj = forkStates.value[forkIds[j]]
      const dx = si.x - sj.x
      const dy = si.y - sj.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < ALARM_DISTANCE) {
        const di = devices.value.find(d => d.device_id === forkIds[i])
        const dj = devices.value.find(d => d.device_id === forkIds[j])
        if (di) di.alarm_status = 2
        if (dj) dj.alarm_status = 2
      } else if (dist < WARN_DISTANCE) {
        const di = devices.value.find(d => d.device_id === forkIds[i])
        const dj = devices.value.find(d => d.device_id === forkIds[j])
        if (di && di.alarm_status < 1) di.alarm_status = 1
        if (dj && dj.alarm_status < 1) dj.alarm_status = 1
      }
    }
  }

  forkIds.forEach(id => {
    const si = forkStates.value[id]
    persons.value.forEach(person => {
      const dx = person.pos_x - si.x
      const dy = person.pos_y - si.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < ALARM_DISTANCE) {
        const dev = devices.value.find(d => d.device_id === id)
        if (dev) dev.alarm_status = 2
      } else if (dist < WARN_DISTANCE) {
        const dev = devices.value.find(d => d.device_id === id)
        if (dev && dev.alarm_status < 1) dev.alarm_status = 1
      }
    })
  })
}

function updatePersonPositions() {
  persons.value.forEach(person => {
    if (Math.random() < 0.02) {
      person.direction += (Math.random() - 0.5) * Math.PI
    }

    person.pos_x += Math.cos(person.direction) * person.speed
    person.pos_y += Math.sin(person.direction) * person.speed

    if (person.pos_x <= 50 || person.pos_x >= MAP_COORD_WIDTH - 50) {
      person.direction = Math.PI - person.direction
      person.pos_x = Math.max(50, Math.min(MAP_COORD_WIDTH - 50, person.pos_x))
    }
    if (person.pos_y <= 50 || person.pos_y >= MAP_COORD_HEIGHT - 50) {
      person.direction = -person.direction
      person.pos_y = Math.max(50, Math.min(MAP_COORD_HEIGHT - 50, person.pos_y))
    }
  })
}

function buildForkData() {
  return Object.keys(forkMovementData.value).map(deviceId => {
    const state = forkStates.value[deviceId]
    return {
      name: deviceId,
      value: [state.x, state.y],
      entityType: 'fork',
      rotation: state.direction,
    }
  })
}

function buildPersonData() {
  return persons.value.map(person => ({
    name: person.name,
    value: [person.pos_x, person.pos_y],
    entityType: 'person',
  }))
}

function updateMap() {
  if (!mapChartInstance) return

  updateForkPositions()
  updatePersonPositions()

  const forkData = buildForkData()
  const personData = buildPersonData()
  const warningOuterData = forkData.map(d => {
    const dev = devices.value.find(dd => dd.device_id === d.name)
    const alarmLevel = dev ? dev.alarm_status : 0
    let color = WARNING_OUTER_COLOR
    if (alarmLevel === 2) color = 'rgba(255, 200, 0, 0.55)'
    else if (alarmLevel === 1) color = 'rgba(255, 200, 0, 0.4)'
    return {
      ...d,
      value: d.value,
      itemStyle: { color },
    }
  })
  const warningInnerData = forkData.map(d => {
    const dev = devices.value.find(dd => dd.device_id === d.name)
    const alarmLevel = dev ? dev.alarm_status : 0
    let color = WARNING_INNER_COLOR
    if (alarmLevel === 2) color = 'rgba(255, 0, 0, 0.5)'
    else if (alarmLevel === 1) color = 'rgba(255, 150, 0, 0.35)'
    return {
      ...d,
      value: d.value,
      itemStyle: { color },
    }
  })

  const forkDisplayData = forkData.map(d => {
    return {
      ...d,
      itemStyle: {
        color: FORK_COLOR,
        shadowBlur: 10,
        shadowColor: 'rgba(52, 152, 219, 0.5)',
      },
    }
  })

  mapChartInstance.setOption({
    animation: false,
    series: [
      { data: warningOuterData, symbolSize: WARN_DISTANCE * 2 * coordScale },
      { data: warningInnerData, symbolSize: ALARM_DISTANCE * 2 * coordScale },
      { data: forkDisplayData },
      { data: personData },
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
  coordScale = scale
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
    const newDevices = devicesRes.data.devices || []
    
    newDevices.forEach(dev => {
      if (forkMovementData.value[dev.device_id]) {
        dev.online_status = 1
        const state = forkStates.value[dev.device_id]
        if (state) {
          dev.pos_x = state.x
          dev.pos_y = state.y
        }
      }
    })
    
    devices.value = newDevices
    
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

function getAlarmReason(alarm) {
  if (!alarm) return '人离叉车过近'
  const forks = devices.value.filter(d => forkMovementData.value[d.device_id])
  const forkIds = forks.map(d => d.device_id)
  const alarmFork = forks.find(d => d.device_id === alarm.device_id)
  if (alarmFork) {
    for (const otherFork of forks) {
      if (otherFork.device_id === alarm.device_id) continue
      const dx = (alarmFork.pos_x || 0) - (otherFork.pos_x || 0)
      const dy = (alarmFork.pos_y || 0) - (otherFork.pos_y || 0)
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 100) {
        return '叉车和叉车距离过近'
      }
    }
  }
  return '人和叉车距离过近'
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

function handleImageError(e) {
  e.target.style.display = 'none'
}

function showAlarmImage(alarm) {
  selectedAlarm.value = alarm
  showImageModal.value = true
}

let socket = null
let trendTimer = null

onMounted(() => {
  mapChartInstance = echarts.init(mapChart.value)
  mapChartInstance.setOption({
    animation: false,
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
      formatter: p => {
        if (p.data.entityType === 'fork') {
          const zone = getZoneName(p.data.value[0], p.data.value[1])
          return `<strong>叉车: ${p.data.name}</strong><br/>区域: ${zone}<br/>位置: (${p.data.value[0].toFixed(0)}, ${p.data.value[1].toFixed(0)})`
        }
        if (p.data.entityType === 'person') {
          return `<strong>行人: ${p.data.name}</strong><br/>位置: (${p.data.value[0].toFixed(0)}, ${p.data.value[1].toFixed(0)})`
        }
        return `<strong>${p.data.name}</strong><br/>状态: ${p.data.statusText}<br/>最后更新: ${p.data.lastSeen}`
      },
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
      name: '警示外圈',
      type: 'scatter',
      coordinateSystem: 'cartesian2d',
      clip: true,
      silent: true,
      z: 1,
      symbolSize: WARN_DISTANCE * 2 * coordScale,
      symbol: 'circle',
      itemStyle: {
        color: WARNING_OUTER_COLOR,
        borderColor: 'transparent',
        borderWidth: 0,
      },
      data: [],
    }, {
      name: '警示内圈',
      type: 'scatter',
      coordinateSystem: 'cartesian2d',
      clip: true,
      silent: true,
      z: 2,
      symbolSize: ALARM_DISTANCE * 2 * coordScale,
      symbol: 'circle',
      itemStyle: {
        color: WARNING_INNER_COLOR,
        borderColor: 'transparent',
        borderWidth: 0,
      },
      data: [],
    }, {
      name: '叉车',
      type: 'scatter',
      coordinateSystem: 'cartesian2d',
      clip: true,
      silent: true,
      z: 5,
      symbolSize: 8,
      symbol: 'path://M0,-8 L6,6 L-6,6 Z',
      symbolRotate: (val, params) => params.data?.rotation || 0,
      itemStyle: {
        color: FORK_COLOR,
        shadowBlur: 10,
        shadowColor: 'rgba(52, 152, 219, 0.5)',
      },
      data: [],
    }, {
      name: '行人',
      type: 'scatter',
      coordinateSystem: 'cartesian2d',
      clip: true,
      silent: true,
      z: 6,
      symbolSize: 3,
      symbol: 'path://M0,-8 L-6,8 M0,-8 L6,8 M0,0 L0,12',
      itemStyle: {
        color: PERSON_COLOR,
        shadowBlur: 5,
        shadowColor: 'rgba(46, 204, 113, 0.3)',
        borderColor: '#fff',
        borderWidth: 1,
      },
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
    updateMap()
    fetchAlarmTrend()
  })

  socket.on('position_update', (data) => {
    if (!data) return
    data.forEach((dev) => {
      if (dev.device_id && forkMovementData.value[dev.device_id]) {
        return
      }
      const index = devices.value.findIndex(d => d.device_id === dev.device_id)
      if (index !== -1) {
        devices.value[index] = { ...devices.value[index], ...dev }
      }
    })
  })

  trendTimer = setInterval(() => {
    fetchAlarmTrend()
  }, 60000)

  // Add movement update timer
  const movementTimer = setInterval(() => {
    updateMap()
  }, 50) // Update every 50ms for smooth animation

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
    if (movementTimer) {
      clearInterval(movementTimer)
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

.kpi-clickable {
  cursor: pointer;
  position: relative;
}

.fork-detail-popup {
  position: absolute;
  left: calc(100% + 8px);
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 14px;
  padding: 12px 14px;
  min-width: 200px;
  box-shadow: 0 8px 32px rgba(140, 120, 180, 0.18);
  z-index: 100;
}

.fork-detail-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(140, 120, 180, 0.1);
}

.fork-detail-row:last-child {
  border-bottom: none;
}

.fork-detail-name {
  font-family: 'DM Sans', sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: #3a3550;
  flex-shrink: 0;
}

.fork-detail-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}

.fork-detail-zone {
  font-size: 11px;
  font-weight: 700;
  color: #6c5ce7;
  background: rgba(108, 92, 231, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.03em;
}

.fork-detail-pos {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #8a8aa8;
  flex: 1;
}

.fork-detail-status {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  color: #2c7051;
  background: rgba(168, 230, 207, 0.26);
}

.fork-detail-status.alarming {
  color: #9f1f1f;
  background: rgba(240, 160, 160, 0.26);
}

.fork-detail-empty {
  font-size: 11px;
  color: #8a8aa8;
  text-align: center;
  padding: 8px 0;
}

.fork-detail-enter-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.fork-detail-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.fork-detail-enter-from {
  opacity: 0;
  transform: translateY(-50%) translateX(-8px);
}

.fork-detail-leave-to {
  opacity: 0;
  transform: translateY(-50%) translateX(-8px);
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

.legend-fork {
  width: 0;
  height: 0;
  border-left: 3px solid transparent;
  border-right: 3px solid transparent;
  border-bottom: 5px solid #3498db;
}

.legend-person {
  width: 6px;
  height: 6px;
  border-left: 1px solid #2ecc71;
  border-right: 1px solid #2ecc71;
  border-bottom: 1px solid #2ecc71;
  background: transparent;
}

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
  line-clamp: 3;
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
