# 对话功能全面增强方案

## 背景问题

用户反馈现有对话功能存在四个核心问题：
1. **无聊天历史**：刷新后对话消失，无持久化存储
2. **对话体验僵硬**：缺乏小助手人设引导，用户不知能做什么
3. **无图表渲染**：无法在对话窗口展示柱状图、雷达图等
4. **查询繁琐**：用户不知道该如何提问才能让 Agent 查到数据

## 设计决策

> [!IMPORTANT]
> **图表方案选择**：后端已有 `pyecharts` 生成 HTML，但前端已安装 `echarts@6`。为获得更好的交互体验，改为**后端传 JSON 数据，前端用 ECharts 渲染**，这样可以支持柱状图、折线图、饼图、雷达图等自由渲染和交互。

> [!IMPORTANT]
> **历史持久化方案**：采用**前端 localStorage** 方案，简单实用。每个用户的会话列表和消息缓存在本地，无需新建数据库表。

---

## 模块 1：聊天历史持久化（前端 localStorage）

### [MODIFY] [ChatPage.vue](file:///G:/PycharmProjects/BankAgent-Pro/frontend/src/views/pages/ChatPage.vue)

- 新增**会话侧栏**：左侧展示历史会话列表，支持新建会话、切换会话、删除会话
- 使用 `localStorage` 缓存会话数据，key 格式：`chat_sessions_{userId}`
- 每条消息包含 `role`、`content`、[chart](file:///G:/PycharmProjects/BankAgent-Pro/backend/app/graphs/tools.py#310-370)、[sql](file:///G:/PycharmProjects/BankAgent-Pro/backend/app/graphs/stream_event.py#26-30)、[sources](file:///G:/PycharmProjects/BankAgent-Pro/backend/app/graphs/stream_event.py#56-60)、`chartData`、`timestamp`
- 切换会话时从 localStorage 加载历史消息
- 发送消息时自动保存到 localStorage

---

## 模块 2：AI 小助手人设 & 引导优化

### [MODIFY] [ChatPage.vue](file:///G:/PycharmProjects/BankAgent-Pro/frontend/src/views/pages/ChatPage.vue)

- 重写**欢迎区域**：展示助手头像、名称、能力介绍
- 能力卡片分四个方向：
  - 📊 **数据查询** — "查询30岁以下的客户有多少？"
  - 📈 **统计分析** — "各职业的转化率是多少？"
  - 📚 **知识问答** — "银行定期存款产品有哪些特点？"
  - 🔮 **智能预测** — "预测某客户是否会认购定期存款"
- 引入 `marked` 库渲染助手回复的 Markdown 格式（已安装但未使用）
- 增强消息气泡样式，支持 Markdown 内容展示

---

## 模块 3：ECharts 图表渲染

### [MODIFY] [stream_event.py](file:///G:/PycharmProjects/BankAgent-Pro/backend/app/graphs/stream_event.py)

- 新增 `chart_data()` 静态方法，传输 JSON 格式图表配置：
  ```python
  @staticmethod
  def chart_data(chart_type, x_data, y_data, title, series_name=""):
      """图表数据事件（JSON格式，前端用 ECharts 渲染）"""
  ```

### [MODIFY] [two_stage_workflow.py](file:///G:/PycharmProjects/BankAgent-Pro/backend/app/graphs/two_stage_workflow.py)

- 在 [_handle_query()](file:///G:/PycharmProjects/BankAgent-Pro/backend/app/graphs/two_stage_workflow.py#118-165) 方法中，当 `final_state` 包含 `sql_result` / `generated_sql` / `chart_html` 时：
  - yield `StreamEvent.sql(generated_sql)`
  - yield `StreamEvent.chart_data(chart_type, x_data, y_data, title)` 将原始数据发送到前端
  - 而不仅仅 yield answer

### [MODIFY] [ChatPage.vue](file:///G:/PycharmProjects/BankAgent-Pro/frontend/src/views/pages/ChatPage.vue)

- 接收 `chart_data` SSE 事件
- 使用 ECharts（已安装 `echarts@6`）渲染图表
- 支持图表类型：柱状图（bar）、折线图（line）、饼图（pie）、雷达图（radar）
- 图表在消息气泡内展示，注册 `onUnmounted` 清理资源

---

## 模块 4：数据查询提示引导

### [MODIFY] [ChatPage.vue](file:///G:/PycharmProjects/BankAgent-Pro/frontend/src/views/pages/ChatPage.vue)

- 在输入区域上方增加**可折叠查询指南面板**
- 指南内容分类展示用户可用话术：
  - **筛选查询**："查询30岁以下的客户"、"查看已婚客户数据"
  - **统计分析**："各职业的转化率是多少"、"年龄的平均值和中位数"
  - **可视化**："用柱状图展示各学历人数"、"用饼图展示职业分布"
  - **知识库**："银行的定期存款产品有哪些特点"
- 点击话术示例自动填入输入框

---

## 验证计划

### 手动验证（浏览器测试）

1. **启动开发服务器**：
   - 后端：`cd G:\PycharmProjects\BankAgent-Pro && python -m uvicorn backend.app:app --reload --port 8000`
   - 前端：`cd G:\PycharmProjects\BankAgent-Pro\frontend && npm run dev`

2. **聊天历史持久化验证**：
   - 打开对话页面，发送消息
   - 刷新浏览器，确认消息仍然存在
   - 新建会话，确认会话列表正确
   - 切换会话，确认消息正确加载

3. **AI 小助手引导验证**：
   - 进入空对话页面，确认欢迎区域展示助手能力卡片
   - 点击能力卡片中的示例话术，确认自动填入输入框并发送

4. **图表渲染验证**：
   - 发送 "各职业人数分布" 等查询
   - 确认对话窗口内出现 ECharts 柱状图

5. **查询指南验证**：
   - 确认输入框上方出现查询指南面板
   - 点击示例话术，确认自动填入输入框
