<template>
  <div class="trend-page">
    <main class="main-content-inner">

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
        />

      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../lib/api'
import LineChart from '../components/LineChart.vue'

const range = ref('day')

const chartLabels = ref([])
const chartSeries = ref([])

// 🔥 三台叉车
const devices = ['FORK-001', 'FORK-002', 'FORK-003']

const ranges = [
  { label: '日', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' }
]

const rangeText = computed(() => {
  return ranges.find(r => r.value === range.value)?.label
})



async function fetchData() {
  try {
    const res = await api.get('/api/trend', {
      params: { type: range.value }
    })

    const data = res.data || {}

    // ✅ X轴
    chartLabels.value = data.labels || []

    // ✅ 三台车
    chartSeries.value = [
      {
        name: 'FORK-001',
        data: data.fork1 || [],
        color: '#b8a9e8'
      },
      {
        name: 'FORK-002',
        data: data.fork2 || [],
        color: '#D0F578'
      },
      {
        name: 'FORK-003',
        data: data.fork3 || [],
        color: '#f0a0a0'   // 👈 新颜色（红）
      }
    ]

  } catch (e) {
    console.error('趋势数据加载失败', e)
  }
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

/* ⚠️ 注意：不能再用 Dashboard 的 main-content */
.main-content-inner {
  padding: 28px 32px;
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
