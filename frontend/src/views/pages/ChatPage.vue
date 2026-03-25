<template>
  <div class="page">
    <!-- 聊天容器 (沉浸式全屏) -->
    <section class="chat-container">
      <!-- 会话侧栏 -->
      <div class="session-sidebar" :class="{ collapsed: sidebarCollapsed }">
        <div class="sidebar-header">
          <button class="new-chat-btn" @click="createNewSession">
            <el-icon><Plus /></el-icon>
            <span v-show="!sidebarCollapsed">新建对话</span>
          </button>
          <button class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed">
            <el-icon>
              <DArrowLeft v-if="!sidebarCollapsed" />
              <DArrowRight v-else />
            </el-icon>
          </button>
        </div>

        <div class="sessions-list" v-show="!sidebarCollapsed">
          <div
            v-for="session in sessions"
            :key="session.id"
            :class="['session-item', { active: session.id === currentSessionId }]"
            @click="switchSession(session.id)"
          >
            <div class="session-title">
              <el-icon><ChatDotRound /></el-icon>
              <span class="session-name">{{ session.title || '新对话' }}</span>
            </div>
            <div class="session-meta">
              <span class="session-time">{{ formatTime(session.updatedAt) }}</span>
              <el-icon class="delete-icon" @click.stop="deleteSession(session.id)">
                <Delete />
              </el-icon>
            </div>
          </div>
        </div>

        <div class="sidebar-footer" v-show="!sidebarCollapsed">
          <router-link to="/dashboard" class="exit-chat-btn">
            <el-icon><House /></el-icon>
            返回管理系统
          </router-link>
        </div>
      </div>

      <!-- 主聊天区域 -->
      <div class="chat-main">
        <!-- 模式切换 -->
        <div class="mode-toggle">
          <button
            :class="['mode-btn', { active: chatMode === 'data' }]"
            @click="chatMode = 'data'"
          >
            <el-icon><TrendCharts /></el-icon>
            数据查询
          </button>
          <button
            :class="['mode-btn', { active: chatMode === 'knowledge' }]"
            @click="chatMode = 'knowledge'"
          >
            <el-icon><Reading /></el-icon>
            知识库
          </button>
        </div>

        <!-- 消息列表 -->
        <div class="messages-list" ref="messagesRef">
          <!-- 欢迎界面 -->
          <div v-if="messages.length === 0" class="welcome-state">
            <div class="assistant-avatar">
              <div class="avatar-inner">
                <span class="avatar-emoji">🎀</span>
              </div>
            </div>
            <h3 class="welcome-title">你好，我是小贝壳</h3>
            <p class="welcome-subtitle">你的银行数据智能分析助手</p>
            <p class="welcome-desc">我可以帮你分析数据、查询知识库，试试问我：</p>

            <!-- 能力卡片 -->
            <div class="ability-cards">
              <div class="ability-card" @click="sendSuggestion('查询30岁以下的客户有哪些？')">
                <div class="card-icon">
                  <el-icon><Search /></el-icon>
                </div>
                <div class="card-content">
                  <h4>数据查询</h4>
                  <p>查询30岁以下的客户</p>
                </div>
              </div>

              <div class="ability-card" @click="sendSuggestion('各职业的转化率是多少？')">
                <div class="card-icon">
                  <el-icon><DataAnalysis /></el-icon>
                </div>
                <div class="card-content">
                  <h4>统计分析</h4>
                  <p>各职业的转化率</p>
                </div>
              </div>

              <div class="ability-card" @click="sendSuggestion('用柱状图展示各学历人数分布')">
                <div class="card-icon">
                  <el-icon><Histogram /></el-icon>
                </div>
                <div class="card-content">
                  <h4>可视化</h4>
                  <p>柱状图展示数据</p>
                </div>
              </div>

              <div class="ability-card" @click="sendSuggestion('银行的定期存款产品有哪些特点？')">
                <div class="card-icon">
                  <el-icon><Reading /></el-icon>
                </div>
                <div class="card-content">
                  <h4>知识问答</h4>
                  <p>查询产品知识</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 消息 -->
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
            <div v-if="msg.role === 'assistant'" class="message-content">
              <div class="assistant-badge">
                <div class="badge-avatar">🎀</div>
                <span class="badge-name">小贝壳</span>
              </div>
              <!-- Markdown 渲染的内容 -->
              <div class="message-text markdown-content" v-html="renderMarkdown(msg.content)"></div>
              <!-- 图表 -->
              <div v-if="msg.chartData" class="chart-box">
                <div :id="`chart-${index}`" class="echarts-container"></div>
              </div>
              <!-- 来源 -->
              <div v-if="msg.sources && msg.sources.length > 0" class="sources-box">
                <div class="sources-title">
                  <el-icon><DocumentCopy /></el-icon>
                  知识来源 ({{ msg.sources.length }})
                </div>
                <div v-for="(source, idx) in msg.sources" :key="idx" class="source-item">
                  <span class="source-index">{{ idx + 1 }}</span>
                  <div class="source-content">{{ source.content }}</div>
                </div>
              </div>
              <!-- SQL -->
              <div v-if="msg.sql" class="sql-box">
                <div class="sql-title">
                  <el-icon><Tickets /></el-icon>
                  已执行 SQL
                </div>
                <pre>{{ msg.sql }}</pre>
              </div>
              <div class="message-time">{{ formatMessageTime(msg.timestamp) }}</div>
            </div>
            <div v-else class="message-content user-content">
              <div class="message-text">{{ msg.content }}</div>
              <div class="message-time">{{ formatMessageTime(msg.timestamp) }}</div>
            </div>
          </div>

          <!-- 加载动画 -->
          <div v-if="loading" class="message assistant">
            <div class="message-content">
              <div class="assistant-badge">
                <div class="badge-avatar">🎀</div>
                <span class="badge-name">小贝壳</span>
              </div>
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 查询指南（可折叠） -->
        <div class="query-guide" v-if="!guideCollapsed">
          <div class="guide-header">
            <span class="guide-title">
              <el-icon><Compass /></el-icon>
              查询指南
            </span>
            <el-icon class="guide-close" @click="guideCollapsed = true"><Close /></el-icon>
          </div>
          <div class="guide-content">
            <div class="guide-section">
              <span class="guide-label">筛选查询</span>
              <div class="guide-examples">
                <span class="guide-chip" @click="sendSuggestion('查询30岁以下的客户有哪些？')">
                  查询30岁以下客户
                </span>
                <span class="guide-chip" @click="sendSuggestion('查看已婚客户的数据')">
                  已婚客户数据
                </span>
              </div>
            </div>
            <div class="guide-section">
              <span class="guide-label">统计分析</span>
              <div class="guide-examples">
                <span class="guide-chip" @click="sendSuggestion('各职业的转化率是多少？')">
                  职业转化率
                </span>
                <span class="guide-chip" @click="sendSuggestion('年龄的平均值和中位数是多少？')">
                  年龄统计
                </span>
              </div>
            </div>
            <div class="guide-section">
              <span class="guide-label">可视化</span>
              <div class="guide-examples">
                <span class="guide-chip" @click="sendSuggestion('用柱状图展示各学历人数分布')">
                  柱状图展示
                </span>
                <span class="guide-chip" @click="sendSuggestion('用饼图展示职业分布')">
                  饼图展示
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <button
            v-if="guideCollapsed"
            class="guide-toggle-btn"
            @click="guideCollapsed = false"
            title="查看查询指南"
          >
            <el-icon><Compass /></el-icon>
          </button>
          <input
            v-model="inputMessage"
            @keyup.enter="sendMessage"
            type="text"
            placeholder="试试问我：查询30岁以下的客户有哪些？"
            :disabled="loading"
            class="chat-input"
          />
          <button
            class="send-btn"
            @click="sendMessage"
            :disabled="!inputMessage.trim() || loading"
          >
            <el-icon v-if="!inputMessage.trim() || loading"><Loading /></el-icon>
            <el-icon v-else><Promotion /></el-icon>
            <span>发送</span>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { marked } from 'marked'
import * as echarts from 'echarts'
import {
  Plus, DArrowLeft, DArrowRight, ChatDotRound, Delete, TrendCharts,
  Reading, Search, DataAnalysis, Histogram, DocumentCopy, Tickets,
  Compass, Close, Promotion, Loading, House
} from '@element-plus/icons-vue'

// 状态管理
const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const messagesRef = ref(null)
const chatMode = ref('data')
const sidebarCollapsed = ref(false)
const guideCollapsed = ref(false)

// 会话管理
const sessions = ref([])
const currentSessionId = ref(null)
const STORAGE_KEY = 'chat_sessions'

// ECharts 实例
const chartInstances = ref(new Map())

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`

  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const formatMessageTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// Markdown 渲染
const renderMarkdown = (content) => {
  if (!content) return ''
  return marked.parse(content)
}

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

// LocalStorage 操作
const loadSessions = () => {
  const userId = localStorage.getItem('userId') || 'default'
  const data = localStorage.getItem(`${STORAGE_KEY}_${userId}`)
  if (data) {
    sessions.value = JSON.parse(data)
  }
}

const saveSessions = () => {
  const userId = localStorage.getItem('userId') || 'default'
  localStorage.setItem(`${STORAGE_KEY}_${userId}`, JSON.stringify(sessions.value))
}

const loadMessages = (sessionId) => {
  const session = sessions.value.find(s => s.id === sessionId)
  if (session) {
    messages.value = session.messages || []
  }
}

// 会话管理
const createNewSession = () => {
  const newSession = {
    id: Date.now().toString(),
    title: '',
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now()
  }
  sessions.value.unshift(newSession)
  currentSessionId.value = newSession.id
  messages.value = []
  saveSessions()
}

const switchSession = (sessionId) => {
  currentSessionId.value = sessionId
  loadMessages(sessionId)
}

const deleteSession = (sessionId) => {
  sessions.value = sessions.value.filter(s => s.id !== sessionId)
  if (currentSessionId.value === sessionId) {
    if (sessions.value.length > 0) {
      switchSession(sessions.value[0].id)
    } else {
      createNewSession()
    }
  }
  saveSessions()
}

const updateSessionTitle = (sessionId, firstMessage) => {
  const session = sessions.value.find(s => s.id === sessionId)
  if (session && !session.title) {
    session.title = firstMessage.slice(0, 20) + (firstMessage.length > 20 ? '...' : '')
    saveSessions()
  }
}

const saveCurrentMessage = (role, content, extra = {}) => {
  if (!currentSessionId.value) return

  const session = sessions.value.find(s => s.id === currentSessionId.value)
  if (session) {
    const msg = {
      role,
      content,
      timestamp: Date.now(),
      ...extra
    }
    session.messages.push(msg)
    session.updatedAt = Date.now()
    saveSessions()
  }
}

// 渲染图表
const renderChart = (index, chartData) => {
  nextTick(() => {
    const chartId = `chart-${index}`
    const chartDom = document.getElementById(chartId)
    if (!chartDom) return

    // 清理旧实例
    if (chartInstances.value.has(chartId)) {
      chartInstances.value.get(chartId).dispose()
    }

    const chart = echarts.init(chartDom)
    chartInstances.value.set(chartId, chart)

    const option = {
      title: {
        text: chartData.title || '',
        left: 'center',
        textStyle: { fontSize: 14, color: '#666' }
      },
      tooltip: {
        trigger: chartData.chart_type === 'pie' ? 'item' : 'axis'
      },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: chartData.chart_type !== 'pie' ? {
        type: 'category',
        data: chartData.x_data,
        axisLine: { lineStyle: { color: '#E8E8E8' } },
        axisLabel: {
          color: '#8C8C8C',
          interval: 'auto',
          hideOverlap: true,
          rotate: 0,
          formatter: (val) => val.length > 6 ? val.slice(0, 6) + '...' : val
        }
      } : undefined,
      yAxis: chartData.chart_type !== 'pie' ? {
        type: 'value',
        axisLabel: { color: '#8C8C8C' },
        splitLine: { lineStyle: { color: '#F5F5F7', type: 'dashed' } }
      } : undefined,
      dataZoom: chartData.chart_type === 'bar' && chartData.x_data?.length > 15 ? [
        { type: 'inside', start: 0, end: 50 },
        { type: 'slider', show: false }
      ] : undefined,
      series: [{
        name: chartData.series_name || '',
        type: chartData.chart_type,
        data: chartData.chart_type === 'pie'
          ? chartData.x_data.map((name, i) => ({ name, value: chartData.y_data[i] }))
          : chartData.y_data,
        itemStyle: {
          borderRadius: chartData.chart_type === 'bar' ? [6, 6, 0, 0] : 0,
          color: chartData.chart_type === 'bar'
            ? { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
                { offset: 0, color: '#D9D9D9' },
                { offset: 1, color: '#8C8C8C' }
              ]}
            : '#8C8C8C'
        },
        smooth: chartData.chart_type === 'line',
        radius: chartData.chart_type === 'pie' ? ['40%', '70%'] : undefined
      }]
    }

    chart.setOption(option)

    // 响应式
    const resizeHandler = () => chart.resize()
    window.addEventListener('resize', resizeHandler)
    chartDom._resizeHandler = resizeHandler
  })
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return

  const userMsg = inputMessage.value
  messages.value.push({ role: 'user', content: userMsg, timestamp: Date.now() })
  saveCurrentMessage('user', userMsg)

  // 更新会话标题
  updateSessionTitle(currentSessionId.value, userMsg)

  inputMessage.value = ''
  loading.value = true
  await scrollToBottom()

  const assistantMsg = {
    role: 'assistant',
    content: '',
    chartData: null,
    sql: null,
    sources: null,
    timestamp: Date.now()
  }
  messages.value.push(assistantMsg)

  try {
    const response = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: userMsg,
        user_id: localStorage.getItem('userId') || 'default',
        session_id: currentSessionId.value,
        history: []
      })
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'text') assistantMsg.content += data.content
            else if (data.type === 'answer') assistantMsg.content = data.content
            else if (data.type === 'sql') assistantMsg.sql = data.sql
            else if (data.type === 'chart_data') {
              assistantMsg.chartData = data
              renderChart(messages.value.length - 1, data)
            }
            else if (data.type === 'sources') assistantMsg.sources = data.sources
            else if (data.type === 'error') assistantMsg.content = data.message
            else if (data.type === 'done') {
              loading.value = false
              saveCurrentMessage('assistant', assistantMsg.content, {
                chartData: assistantMsg.chartData,
                sql: assistantMsg.sql,
                sources: assistantMsg.sources
              })
              await scrollToBottom()
              return
            }
            await scrollToBottom()
          } catch (e) {}
        }
      }
    }
  } catch (error) {
    console.error('Chat error:', error)
    assistantMsg.content = '抱歉，遇到了一些问题，请稍后再试。'
  } finally {
    loading.value = false
    saveCurrentMessage('assistant', assistantMsg.content, {
      chartData: assistantMsg.chartData,
      sql: assistantMsg.sql,
      sources: assistantMsg.sources
    })
    await scrollToBottom()
  }
}

const sendSuggestion = (text) => {
  inputMessage.value = text
  sendMessage()
}

// 初始化
onMounted(() => {
  loadSessions()
  if (sessions.value.length === 0) {
    createNewSession()
  } else {
    currentSessionId.value = sessions.value[0].id
    loadMessages(currentSessionId.value)
    // 渲染已有图表
    nextTick(() => {
      messages.value.forEach((msg, index) => {
        if (msg.chartData) {
          renderChart(index, msg.chartData)
        }
      })
    })
  }
})

// 清理
onUnmounted(() => {
  chartInstances.value.forEach(chart => chart.dispose())
  chartInstances.value.clear()
})
</script>

<style scoped>
/* ============================================================
   整体页面结构
   ============================================================ */
.page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  position: relative;
  background: var(--color-bg-page);
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px dashed var(--color-border);
}

.exit-chat-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.2s ease;
  text-decoration: none;
}

.exit-chat-btn:hover {
  color: var(--color-text-primary);
}

/* ============================================================
   聊天主容器
   ============================================================ */
.chat-container {
  background: var(--color-bg-page);
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ============================================================
   会话侧栏
   ============================================================ */
.session-sidebar {
  width: 260px;
  background: transparent;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  border-right: 1px dashed var(--color-border);
}

.session-sidebar.collapsed {
  width: 56px;
}

.sidebar-header {
  padding: 16px;
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--color-border-light);
}

.new-chat-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-base);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.new-chat-btn:hover {
  background: var(--color-primary-dark);
  border-color: var(--color-border);
}

.collapse-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-base);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.collapse-btn:hover {
  background: var(--color-bg-container);
  color: var(--color-text-primary);
}

.sessions-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.session-item {
  padding: 12px;
  margin-bottom: 8px;
  background: transparent;
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: all 0.2s ease;
}

.session-item:hover {
  background: var(--color-bg-container);
}

.session-item.active {
  background: var(--color-bg-container);
  border: 1px solid var(--color-primary-light);
}

.session-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: 6px;
}

.session-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.session-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.delete-icon {
  opacity: 0;
  transition: opacity 0.2s ease;
  cursor: pointer;
}

.session-item:hover .delete-icon {
  opacity: 1;
}

.delete-icon:hover {
  color: var(--color-primary);
}

/* ============================================================
   主聊天区域
   ============================================================ */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px 40px;
  background: var(--color-bg-container);
}

/* ============================================================
   分段控件 (模式切换)
   ============================================================ */
.mode-toggle {
  display: inline-flex;
  background: var(--color-bg-page);
  padding: 4px;
  border-radius: 12px;
  margin-bottom: 20px;
  align-self: flex-start;
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  background: transparent;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.mode-btn.active {
  background: var(--color-bg-container);
  color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* ============================================================
   消息列表区域
   ============================================================ */
.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.messages-list::-webkit-scrollbar {
  width: 6px;
}
.messages-list::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
}

/* ============================================================
   欢迎界面
   ============================================================ */
.welcome-state {
  text-align: center;
  padding: 60px 40px;
}

.assistant-avatar {
  margin-bottom: 24px;
}

.avatar-inner {
  width: 80px;
  height: 80px;
  margin: 0 auto;
  background: var(--color-bg-container);
  border: 1px solid var(--color-border-light);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}

.avatar-emoji {
  font-size: 40px;
}

.welcome-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.welcome-subtitle {
  font-size: 15px;
  color: var(--color-primary);
  margin-bottom: 16px;
  font-weight: 500;
}

.welcome-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 40px;
}

/* 能力卡片 */
.ability-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  max-width: 600px;
  margin: 0 auto;
}

.ability-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-large);
  cursor: pointer;
  transition: all 0.3s ease;
}

.ability-card:hover {
  background: var(--color-bg-container);
  border-color: var(--color-primary-light);
  transform: translateY(-2px);
  box-shadow: var(--shadow-base);
}

.card-icon {
  width: 48px;
  height: 48px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: var(--color-primary);
  flex-shrink: 0;
}

.card-content h4 {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.card-content p {
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* ============================================================
   聊天气泡
   ============================================================ */
.message {
  margin-bottom: 24px;
  display: flex;
}

.message.assistant {
  justify-content: flex-start;
}

.message.user {
  justify-content: flex-end;
}

.message-content {
  max-width: 80%;
  padding: 16px 20px;
  font-size: 15px;
  line-height: 1.6;
  word-wrap: break-word;
}

.message.assistant .message-content {
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  border-radius: 20px 20px 20px 6px;
}

.message.user .message-content {
  background: var(--color-primary);
  color: #ffffff;
  border-radius: 20px 20px 6px 20px;
}

/* 助手标识 */
.assistant-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-light);
}

.badge-avatar {
  width: 28px;
  height: 28px;
  background: var(--color-bg-container);
  border: 1px solid var(--color-border-light);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.badge-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
}

/* Markdown 内容 */
.markdown-content {
  color: var(--color-text-primary);
}

.markdown-content :deep(p) {
  margin: 8px 0;
}

.markdown-content :deep(strong) {
  color: var(--color-primary);
  font-weight: 600;
}

.markdown-content :deep(code) {
  padding: 2px 6px;
  background: var(--color-bg-page);
  border-radius: 4px;
  font-size: 13px;
}

.markdown-content :deep(pre) {
  padding: 12px;
  background: var(--color-bg-page);
  border-radius: var(--radius-base);
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

/* 消息时间 */
.message-time {
  font-size: 11px;
  color: var(--color-text-placeholder);
  margin-top: 8px;
}

.message.user .message-time {
  text-align: right;
  color: rgba(255, 255, 255, 0.7);
}

/* ============================================================
   图表容器
   ============================================================ */
.chart-box {
  margin-top: 16px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-large);
}

.echarts-container {
  width: 100%;
  height: 380px;
}

/* ============================================================
   来源和SQL框
   ============================================================ */
.sources-box,
.sql-box {
  margin-top: 12px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-large);
}

.sources-title,
.sql-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.source-item {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 14px;
}

.source-item:last-child {
  margin-bottom: 0;
}

.source-index {
  width: 24px;
  height: 24px;
  background: var(--color-bg-page);
  color: var(--color-text-regular);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.sql-box pre {
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 13px;
  color: var(--color-primary);
  white-space: pre-wrap;
  margin: 0;
}

/* ============================================================
   查询指南
   ============================================================ */
.query-guide {
  margin-top: 16px;
  padding: 16px;
  background: var(--color-bg-container);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-large);
}

.guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.guide-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary);
}

.guide-close {
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: color 0.2s ease;
}

.guide-close:hover {
  color: var(--color-text-primary);
}

.guide-content {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.guide-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.guide-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.guide-examples {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.guide-chip {
  padding: 6px 14px;
  background: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  font-size: 13px;
  color: var(--color-text-regular);
  cursor: pointer;
  transition: all 0.2s ease;
}

.guide-chip:hover {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

/* ============================================================
   输入框区域
   ============================================================ */
.input-area {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border-light);
}

.guide-toggle-btn {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-large);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.guide-toggle-btn:hover {
  background: var(--color-bg-container);
  border-color: var(--color-border);
  color: var(--color-primary);
}

.chat-input {
  flex: 1;
  padding: 14px 20px;
  background: var(--color-bg-page);
  border: 1px solid transparent;
  border-radius: var(--radius-large);
  font-size: 15px;
  font-family: inherit;
  color: var(--color-text-primary);
  transition: all 0.3s ease;
}

.chat-input:focus {
  outline: none;
  background: var(--color-bg-container);
  border-color: var(--color-border);
  box-shadow: 0 0 0 4px rgba(0, 0, 0, 0.02);
}

.send-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 24px;
  background: var(--color-primary);
  color: #ffffff;
  font-weight: 600;
  font-size: 15px;
  border: none;
  border-radius: var(--radius-large);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.send-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: scale(0.96);
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* ============================================================
   加载动画
   ============================================================ */
.typing-indicator {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: var(--color-text-secondary);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
.typing-indicator span:nth-child(3) { animation-delay: 0s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>
