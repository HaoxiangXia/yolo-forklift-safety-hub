<template>
  <div ref="chartRef" class="line-chart"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  series: {
    type: Array,
    required: true,
  },
  labels: {
    type: Array,
    default: () => Array.from({ length: 24 }, (_, i) => `${i}:00`),
  },
  height: {
    type: String,
    default: '200px',
  },
  showLegend: {
    type: Boolean,
    default: true,
  },
})

const chartRef = ref(null)
let chartInstance = null

const defaultColors = [
  { line: '#b8a9e8', area: ['rgba(184,169,232,0.18)', 'rgba(184,169,232,0.02)'] },
  { line: '#D0F578', area: ['rgba(208,245,120,0.16)', 'rgba(208,245,120,0.02)'] },
]

function renderChart() {
  if (!chartInstance) return

  chartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.85)',
      borderColor: 'rgba(243, 238, 238, 0.86)',
      borderWidth: 1,
      textStyle: { color: '#dad8e6', fontSize: 12 },
    },
    axisPointer: {
      type: 'shadow',
      shadowStyle: { color: 'rgba(184, 169, 232, 0.12)' },
    },
    legend: props.showLegend
      ? {
          data: props.series.map(s => s.name),
          textStyle: { color: '#0f0f10', fontSize: 15 },
          top: 0,
          itemWidth: 14,
          itemHeight: 3,
        }
      : undefined,
    grid: { left: 36, right: 16, bottom: 28, top: props.showLegend ? 36 : 16 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.labels,
      axisLine: { lineStyle: { color: 'rgba(184,169,232,0.18)' } },
      axisTick: { show: false },
      axisLabel: { color: '#9890b0', fontSize: 10, margin: 8 },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#9890b0', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(184,169,232,0.10)', type: 'dashed' } },
    },
    series: props.series.map((s, i) => {
      const color = s.color || defaultColors[i]?.line || defaultColors[0].line
      const areaColor = s.areaColor || defaultColors[i]?.area || defaultColors[0].area
      return {
        name: s.name,
        type: 'line',
        data: s.data,
        smooth: 0.4,
        showSymbol: false,
        lineStyle: { color, width: s.lineWidth || 3 },
        emphasis: { focus: 'series', lineStyle: { width: s.emphasisWidth || 5 } },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: areaColor[0] },
            { offset: 1, color: areaColor[1] },
          ]),
        },
      }
    }),
    // 🔹 新增 DataZoom 缩放功能
    dataZoom: [
      {
        type: 'inside', // 鼠标滚轮 / 手势缩放
        start: 80,       // 默认显示最后 20%
        end: 100,
        zoomLock: false,
      },
      {
        type: 'slider',  // 底部滑动条
        height: 20,
        bottom: 0,
        handleIcon:
          'M8.2,13.3h-1.6v-2.6h1.6V13.3z', // 简洁手柄
        handleSize: '120%',
        start: 80,
        end: 100,
        showDetail: false, // 隐藏阴影
      }
    ]
  })
}

onMounted(() => {
  chartInstance = echarts.init(chartRef.value)
  renderChart()

  const resizeHandler = () => chartInstance?.resize()
  window.addEventListener('resize', resizeHandler)

  onUnmounted(() => {
    window.removeEventListener('resize', resizeHandler)
    chartInstance?.dispose()
  })
})

watch(() => props.series, renderChart, { deep: true })
</script>

<style scoped>
.line-chart {
  width: 100%;
  height: v-bind(height);
  border-radius: 18px;
  overflow: hidden;
}
</style>
