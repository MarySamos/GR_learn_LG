# 两阶段对话架构设计文档

**日期**: 2026-03-19
**作者**: Claude
**状态**: 设计中

---

## 1. 问题背景

当前 BankAgent 的智能对话存在以下问题：
1. **无法追问** - 用户无法对结果进行自然的追问（"为什么"、"分析一下"）
2. **记不住上下文** - 多轮对话时忘记之前的内容和条件
3. **回答生硬** - 像机器人一样，缺乏人性化语气
4. **理解错误** - 经常误解用户问题

**期望目标**: 实现混合模式的对话体验——闲聊时亲切，查询数据时专业。

---

## 2. 架构设计

### 2.1 整体架构

```
用户输入
    ↓
┌─────────────────────────────────────┐
│  第一阶段：对话路由器               │
│  - 判断意图：闲聊 vs 数据查询        │
│  - 维护对话记忆和上下文             │
│  - 处理追问和修正                   │
└─────────────────────────────────────┘
    ↓                    ↓           ↓
闲聊路径              数据查询路径   追问路径
    ↓                    ↓           ↓
┌──────────────┐   ┌──────────────────┐
│ 轻量级对话   │   │ SQL 分析工作流   │
│ LLM (高温)   │   │ (现有流程增强)   │
└──────────────┘   └──────────────────┘
    ↓                    ↓           ↓
    └──────────┬─────────┘           ↓
               ↓               ┌──────────┐
          统一回答输出         │结果分析器│
                              └──────────┘
```

### 2.2 路由决策类型

| 类型 | 说明 | 示例 |
|-----|------|-----|
| `CHAT` | 闲聊、问候 | "你好"、"谢谢"、"你能做什么" |
| `QUERY` | 数据查询 | "查询30岁以下客户"、"统计转化率" |
| `FOLLOWUP` | 追问之前结果 | "为什么"、"分析一下"、"详细说" |
| `CORRECTION` | 修正之前查询 | "不是30岁，是40岁"、"换个条件" |

---

## 3. 核心组件设计

### 3.1 对话路由器 (ConversationRouter)

**文件**: `backend/app/graphs/router.py`

```python
@dataclass
class RouteDecision:
    route_type: Literal["CHAT", "QUERY", "FOLLOWUP", "CORRECTION"]
    confidence: float
    extracted_entities: Dict[str, Any]  # 提取的条件实体
    followup_type: Optional[str] = None  # EXPLAIN/DETAIL/DRILLDOWN

class ConversationRouter:
    async def route(self, message: str, memory: ConversationMemory) -> RouteDecision:
        """
        路由逻辑：
        1. 检测关键词（"查询"、"统计" → QUERY）
        2. 检测追问词（"为什么"、"呢" → FOLLOWUP）
        3. 检测修正词（"不是"、"重新" → CORRECTION）
        4. 默认 → CHAT
        """
```

**路由 Prompt 模板**:
```
你是对话路由器。根据用户输入判断路由类型。

## 输入
用户消息: {message}
对话历史: {history}
当前主题: {current_topic}

## 路由类型
- CHAT: 问候、闲聊、感谢
- QUERY: 数据查询请求
- FOLLOWUP: 追问之前的结果
- CORRECTION: 修正之前的查询

返回 JSON: {"route_type": "...", "confidence": 0.9, "reasoning": "..."}
```

### 3.2 对话记忆管理器 (ConversationMemory)

**文件**: `backend/app/graphs/memory.py`

```python
@dataclass
class ConversationMemory:
    session_id: str
    user_id: str

    # 对话历史
    messages: List[Dict]  # [{"role": "user", "content": "..."}]

    # 查询相关记忆
    current_topic: Optional[str]  # 当前讨论主题，如"30岁以下客户"
    last_query: Optional[str]  # 上一次查询文本
    last_sql: Optional[str]  # 上一次执行的 SQL
    last_result: Optional[List[Dict]]  # 上一次结果数据（缓存）
    last_intent: Optional[str]  # 上一次意图

    # 提及的实体条件
    mentioned_filters: Dict[str, Any]  # {"age": {"op": "<", "value": 30}}

    # 统计信息
    query_count: int = 0

    def should_cache_result(self, result_size: int) -> bool:
        """判断是否缓存结果（小于1000行）"""

    def add_filters(self, filters: Dict):
        """合并新的筛选条件"""

    def clear_results(self):
        """清除结果缓存"""
```

### 3.3 闲聊处理器 (ChatHandler)

**文件**: `backend/app/graphs/chat_handler.py`

```python
class ChatHandler:
    """处理非数据查询的对话"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm  # temperature=0.8

    async def chat(self, message: str, memory: ConversationMemory) -> str:
        prompt = self._build_chat_prompt(message, memory)
        return await self.llm.ainvoke(prompt)

    def _build_chat_prompt(self, message: str, memory: ConversationMemory) -> str:
        return f"""你是 BankAgent，一个亲切友好的银行数据分析助手。

## 你的特点
- 专业但不刻板，可以适当使用 😊 等表情
- 热情帮助用户了解数据
- 如果用户问银行业务知识，尽力回答
- 记住用户之前说过的内容

## 对话历史
{self._format_history(memory.messages)}

## 当前上下文
{self._format_context(memory)}

用户说：{message}

请用友好自然的语气回复："""
```

### 3.4 追问分析器 (FollowupAnalyzer)

**文件**: `backend/app/graphs/followup.py`

```python
class FollowupAnalyzer:
    """分析并处理用户的追问"""

    FOLLOWUP_TYPES = {
        "EXPLAIN": "解释",      # "为什么"、"什么意思"
        "DETAIL": "展开",       # "详细点"、"多说点"
        "DRILLDOWN": "细分",    # "按XX看"、"分组"
        "COMPARE": "对比",      # "和XX比呢"
        "TREND": "趋势",        # "变化趋势"
    }

    async def analyze(self, message: str, memory: ConversationMemory) -> FollowupAction:
        """分析追问类型并生成响应"""
        if not memory.last_result:
            return FollowupAction(type="NEW_QUERY", reason="无历史结果")

        followup_type = await self._detect_followup_type(message, memory)

        return FollowupAction(
            type=followup_type,
            data=memory.last_result,
            context=memory.current_topic
        )

    async def handle_explain(self, action: FollowupAction, memory: ConversationMemory) -> str:
        """解释型追问：分析数据并解释原因"""

    async def handle_drilldown(self, action: FollowupAction, message: str) -> str:
        """下钻型追问：基于当前结果添加分组"""
```

**追问分析 Prompt**:
```
用户说: {message}
上一次查询: {last_query}
上一次结果预览: {result_preview}

这是什么类型的追问？
- EXPLAIN: 要求解释原因/含义
- DETAIL: 要求更多细节
- DRILLDOWN: 要求按某维度细分
- COMPARE: 要求对比
- NOT_FOLLOWUP: 不是追问

返回 JSON: {{"type": "...", "dimension": "..."}}  # dimension 用于 DRILLDOWN
```

### 3.5 语气适配器 (ToneAdapter)

**文件**: `backend/app/graphs/tone.py`

```python
class ToneAdapter:
    """根据内容调整回答语气"""

    def adapt(self, content: str, route_type: str, has_data: bool = False) -> str:
        """
        - CHAT: 亲切 + 适当 emoji
        - QUERY: 专业但友好，加入数据洞察
        - ERROR: 友好提示 + 建议
        """
        if route_type == "CHAT":
            return self._friendly_tone(content)
        elif has_data:
            return self._professional_insight_tone(content)
        else:
            return self._neutral_tone(content)

    def _professional_insight_tone(self, content: str) -> str:
        """专业且有洞察力的语气"""
        # 添加数据洞察语言
        # "从数据来看..."
        # "值得注意的是..."
        # "这说明..."
```

### 3.6 增强版工作流入口

**文件**: `backend/app/graphs/two_stage_workflow.py`

```python
class TwoStageWorkflow:
    """两阶段对话工作流"""

    def __init__(self):
        self.router = ConversationRouter()
        self.chat_handler = ChatHandler(creative_llm)
        self.followup_analyzer = FollowupAnalyzer()
        self.data_workflow = agent_app  # 现有工作流
        self.memory_manager = MemoryManager()
        self.tone_adapter = ToneAdapter()

    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str = "default"
    ) -> AsyncGenerator[StreamEvent, None]:
        """处理用户消息（流式）"""

        # 1. 加载记忆
        memory = await self.memory_manager.get_or_create(session_id, user_id)

        # 2. 路由
        decision = await self.router.route(message, memory)
        yield StreamEvent.intent(decision.route_type)

        # 3. 分发处理
        if decision.route_type == "CHAT":
            response = await self.chat_handler.chat(message, memory)
            yield StreamEvent.answer(response)

        elif decision.route_type == "FOLLOWUP":
            async for chunk in self._handle_followup(decision, message, memory):
                yield chunk

        else:  # QUERY or CORRECTION
            async for chunk in self._handle_query(decision, message, memory):
                yield chunk

        # 4. 更新记忆
        await self.memory_manager.update(memory)

        yield StreamEvent.done()
```

---

## 4. 数据流程

### 4.1 闲聊流程

```
用户: "你好"
  ↓
路由: CHAT
  ↓
ChatHandler: "你好呀！😊 我是 BankAgent，可以帮你分析银行营销数据..."
  ↓
记忆: 更新 messages
```

### 4.2 数据查询流程

```
用户: "查询30岁以下的客户"
  ↓
路由: QUERY
  ↓
记忆: 提取实体 {"age": {"op": "<", "value": 30}}
  ↓
DataWorkflow: 生成 SQL → 执行 → 返回结果
  ↓
ToneAdapter: 适配语气 → "找到了 2534 位 30 岁以下的客户..."
  ↓
记忆: 保存 current_topic, last_query, last_result
```

### 4.3 追问流程

```
用户: "为什么转化率低？"
  ↓
路由: FOLLOWUP (EXPLAIN)
  ↓
FollowupAnalyzer: 分析 last_result 中转化率低的原因
  ↓
ToneAdapter: "从数据来看，这个群体的转化率较低可能是因为..."
  ↓
记忆: 更新 messages
```

### 4.4 下钻流程

```
用户: "按职业细分"
  ↓
路由: FOLLOWUP (DRILLDOWN)
  ↓
FollowupAnalyzer: 识别维度 "job"
  ↓
生成新 SQL: SELECT job, COUNT(*) ... WHERE age < 30 GROUP BY job
  ↓
返回: 各职业的分布数据
```

---

## 5. 文件结构

```
backend/app/graphs/
├── router.py              # 对话路由器（新增）
├── memory.py              # 对话记忆管理（新增）
├── chat_handler.py        # 闲聊处理器（新增）
├── followup.py            # 追问分析器（新增）
├── tone.py                # 语气适配器（新增）
├── two_stage_workflow.py  # 两阶段工作流入口（新增）
├── state.py               # 现有，保留
├── workflow.py            # 现有，保留
├── nodes.py               # 现有，保留
├── prompts.py             # 现有，可能需要调整
└── agents/                # 新增目录
    ├── router_agent.py    # 路由 LLM Agent
    └── chat_agent.py      # 闲聊 LLM Agent

backend/app/api/endpoints/
├── chat.py                # 修改：使用 two_stage_workflow
└── chat_stream.py         # 修改：使用 two_stage_workflow
```

---

## 6. 兼容性

- API 接口保持不变
- 现有 SQL 工作流保留
- Checkpoint 机制复用
- 前端无需改动

---

## 7. 实施计划概要

1. **Phase 1**: 基础组件
   - ConversationRouter
   - ConversationMemory
   - MemoryManager

2. **Phase 2**: 闲聊路径
   - ChatHandler
   - 友好的 Prompt 设计

3. **Phase 3**: 追问处理
   - FollowupAnalyzer
   - 各类追问的处理逻辑

4. **Phase 4**: 集成与优化
   - TwoStageWorkflow
   - ToneAdapter
   - 端到端测试

---

## 8. 成功指标

- 闲聊响应时间 < 1秒（不调用数据工作流）
- 追问识别准确率 > 85%
- 上下文记忆准确率 > 90%
- 用户满意度提升
