<template>
  <div class="trend-page">
    <main class="main-content-inner">

      <!-- 🔹 新增统计磁贴 -->
      <div class="stats-cards">
        <div class="card">
          <div class="title">今日报警高峰</div>
          <div class="value" ref="peak">0</div>
        </div>
        <div class="card">
          <div class="title">累计报警总数</div>
          <div class="value" ref="total">0</div>
        </div>
        <div class="card">
          <div class="title">待处理项</div>
          <div class="value" ref="pending">0</div>
        </div>
      </div>

      <div class="card glass trend-card">

        <!-- Header -->
        <div class="card-header">
          <h3 class="card-title">报警趋势分析</h3>
          <span class="card-meta">{{ rangeText }}</span>
        </div>

        <!-- 控制区 -->
        <div class="controls">
          <div class="tabs">
            <button
              v-for="r in ranges"
              :key="r.value"
              :class="{ active: range === r.value }"
              @click="changeRange(r.value)"
            >
              {{ r.label }}
            </button>
          </div>
        </div>

        <!-- 图表 -->
        <LineChart
          :series="chartSeries"
          :labels="chartLabels"
          :height="'320px'"
          :options="chartOptions"
        />

      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import api from '../lib/api'
import LineChart from '../components/LineChart.vue'

const range = ref('day')

const chartLabels = ref([])
const chartSeries = ref([])

// 🔹 三台叉车
const devices = ['FORK-001', 'FORK-002', 'FORK-003']

const ranges = [
  { label: '日', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' }
]

const rangeText = computed(() => ranges.find(r => r.value === range.value)?.label)

// 🔹 统计数字 DOM 引用
const peak = ref(null)
const total = ref(null)
const pending = ref(null)

// 🔹 ECharts dataZoom 配置
const chartOptions = {
  dataZoom: [
    {
      type: 'slider',
      show: true,
      height: 20,
      handleSize: 16,
      handleStyle: {
        color: '#888',
        borderWidth: 1,
        borderColor: '#aaa',
        borderRadius: 8
      },
      bottom: 10,
      start: 80,
      end: 100,
      showDetail: false
    },
    {
      type: 'inside',
      start: 80,
      end: 100,
      zoomLock: false
    }
  ]
}

// 🔹 获取数据
async function fetchData() {
  try {
    const res = await api.get('/api/trend', {
      params: { type: range.value }
    })

    const data = res.data || {}

    // ✅ X轴
    chartLabels.value = data.labels || []

    // ✅ 三台车折线 + 不同颜色
    chartSeries.value = [
      { name: 'FORK-001', data: data.fork1 || [], color: '#b8a9e8', smooth: true },
      { name: 'FORK-002', data: data.fork2 || [], color: '#D0F578', smooth: true },
      { name: 'FORK-003', data: data.fork3 || [], color: '#f0a0a0', smooth: true } // 红色
    ]

    // 更新统计磁贴
    await nextTick()
    updateStats()

  } catch (e) {
    console.error('趋势数据加载失败', e)
  }
}

// 🔹 更新统计磁贴数字
function updateStats() {
  const allData = chartSeries.value.flatMap(s => s.data)
  const maxVal = Math.max(...allData)
  const sumVal = allData.reduce((acc, v) => acc + v, 0)
  const pendingVal = Math.floor(sumVal * 0.3) // 模拟待处理项

  if (peak.value) peak.value.innerText = maxVal
  if (total.value) total.value.innerText = sumVal
  if (pending.value) pending.value.innerText = pendingVal
}

function changeRange(r) {
  range.value = r
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.trend-page {
  min-height: 100vh;
}

/* ⚠️ 不能再用 Dashboard 的 main-content */
.main-content-inner {
  padding: 28px 32px;
}

/* 🔹 统计磁贴 */
.stats-cards {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.stats-cards .card {
  flex: 1;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  transition: transform 0.2s;
}

.stats-cards .card:hover {
  transform: translateY(-4px);
}

.stats-cards .title {
  font-size: 14px;
  color: #000; /* 🔹 字体黑色 */
  margin-bottom: 8px;
}

.stats-cards .value {
  font-size: 24px;
  font-weight: bold;
  color: #ff4d4f; /* 告警红 */
}

/* 卡片 */
.trend-card {
  padding: 20px;
  animation: fade-in 0.6s ease;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 控制区 */
.controls {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

/* tabs */
.tabs button {
  margin-left: 10px;
  padding: 6px 12px;
  border-radius: 10px;
  border: none;
  background: rgba(255,255,255,0.2);
  cursor: pointer;
  transition: all 0.2s;
  color: #5c5678;
}

.tabs button:hover {
  background: rgba(255,255,255,0.35);
}

.tabs button.active {
  background: rgba(184,169,232,0.45);
  color: #3a3550;
}
</style>
