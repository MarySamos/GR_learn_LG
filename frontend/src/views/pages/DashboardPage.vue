<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p class="page-breadcrumb">数据概览</p>
        <h1 class="page-title">数据仪表盘</h1>
        <p class="page-subtitle">银行营销数据总览</p>
      </div>
      <button class="btn-primary" @click="loadData" :disabled="loading">
        刷新
      </button>
    </header>

    <!-- 统计卡片 -->
    <section class="stats-overview">
      <div class="stat-card-mini animate-in">
        <div class="stat-label">总客户数</div>
          <div class="stat-value">{{ stats.kpi?.total_customers ?? '-' }}</div>
        <div class="stat-change positive">+12.5%</div>
      </div>
      <div class="stat-card-mini animate-in">
        <div class="stat-label">已转化</div>
          <div class="stat-value">{{ convertedCustomers }}</div>
          <div class="stat-change positive">转化率 {{ stats.kpi?.conversion_rate ?? '-' }}%</div>
      </div>
      <div class="stat-card-mini animate-in">
        <div class="stat-label">平均余额</div>
          <div class="stat-value">{{ stats.kpi?.avg_balance ?? '-' }}</div>
        <div class="stat-change">欧元</div>
      </div>
      <div class="stat-card-mini animate-in">
        <div class="stat-label">平均营销次数</div>
        <div class="stat-value">{{ stats.kpi?.avg_campaign ?? '-' }}</div>
        <div class="stat-change">次</div>
      </div>
    </section>

    <!-- 图表区域 -->
    <section class="charts-section">
      <div class="chart-card animate-in">
        <h3>职业分布</h3>
        <div ref="jobChartRef" class="chart-container"></div>
      </div>
      <div class="chart-card animate-in">
        <h3>婚姻状况</h3>
        <div ref="maritalChartRef" class="chart-container"></div>
      </div>
      <div class="chart-card animate-in">
        <h3>教育水平</h3>
        <div ref="eduChartRef" class="chart-container"></div>
      </div>
      <div class="chart-card animate-in">
        <h3>联系结果</h3>
        <div ref="outcomeChartRef" class="chart-container"></div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, nextTick } from 'vue'
import api from '../../api'
import * as echarts from 'echarts'

const loading = ref(false)
const stats = ref({})
const convertedCustomers = computed(() => {
  const total = stats.value?.kpi?.total_customers
  const rate = stats.value?.kpi?.conversion_rate
  if (typeof total !== 'number' || typeof rate !== 'number') return '-'
  return Math.round((total * rate) / 100)
})

const jobChartRef = ref(null)
const maritalChartRef = ref(null)
const eduChartRef = ref(null)
const outcomeChartRef = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    const response = await api.get('/api/v1/dashboard/stats')
    stats.value = response.data
  } catch (error) {
    console.error('Failed to load stats:', error)
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  // 极简冷色调
  const colorPalette = ['#6C6C6C', '#8C8C8C', '#B4B4B4', '#D9D9D9'];

  const initChart = (refVal, option) => {
    if (refVal.value) {
      const chart = echarts.init(refVal.value)
      chart.setOption(option)
      window.addEventListener('resize', () => chart.resize())
      return chart
    }
  }

  initChart(jobChartRef, {
    tooltip: { trigger: 'item' },
    color: colorPalette,
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 1048, name: '管理员' },
        { value: 1921, name: '技术人员' },
        { value: 2678, name: '蓝领' }
      ]
    }]
  })

  initChart(maritalChartRef, {
    tooltip: { trigger: 'item' },
    color: colorPalette,
    series: [{
      type: 'pie',
      radius: '60%',
      data: [
        { value: 3048, name: '已婚' },
        { value: 1521, name: '单身' },
        { value: 878, name: '离异' }
      ]
    }]
  })

  initChart(eduChartRef, {
    tooltip: { trigger: 'axis' },
    color: ['#8C8C8C'],
    xAxis: { type: 'category', data: ['大学', '高中', '初中', '未知'] },
    yAxis: { type: 'value' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    series: [{
      type: 'bar',
      barWidth: '40%',
      data: [1200, 2000, 1500, 800]
    }]
  })

  initChart(outcomeChartRef, {
    tooltip: { trigger: 'axis' },
    color: ['#B4B4B4'],
    xAxis: { type: 'category', data: ['成功', '失败', '其他'] },
    yAxis: { type: 'value' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    series: [{
      type: 'line',
      smooth: true,
      data: [320, 800, 450],
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(180, 180, 180, 0.4)' },
          { offset: 1, color: 'rgba(180, 180, 180, 0)' }
        ])
      }
    }]
  })
}

onMounted(async () => {
  await loadData()
  await nextTick()
  renderCharts()
})
</script>

<style scoped>
.stats-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

.stat-card-mini {
  background: var(--color-bg-container);
  border-radius: var(--radius-large);
  padding: 24px;
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
  margin-bottom: 12px;
}

.stat-value {
  font-size: 2rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.stat-change {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.stat-change.positive {
  color: var(--color-success);
}

.charts-section {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.chart-card {
  background: var(--color-bg-container);
  border-radius: var(--radius-large);
  padding: 24px;
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
}

.chart-card h3 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--color-text-primary);
}

.chart-container {
  height: 200px;
}
</style>
