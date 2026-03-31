"""LangGraph 智能体 Prompt 模板.

包含 Few-Shot 示例和优化的提示词模板
"""

# ========== 数据库 Schema 描述（精简版）==========
MARKETING_DATA_SCHEMA = """
表名：marketing_data（银行营销数据表）

核心字段：
- id: 唯一标识符
- age: 客户年龄（整数）
- job: 职业（admin, technician, services, management, retired, student, blue-collar, self-employed, unemployed, housemaid, entrepreneur）
- marital: 婚姻状况（married, single, divorced）
- education: 教育程度（primary, secondary, tertiary, unknown）
- default_credit: 是否违约（yes/no）
- balance: 账户余额（整数，旧版数据）
- housing: 是否有住房贷款（yes/no）
- loan: 是否有个人贷款（yes/no）
- contact: 联系方式（cellular, telephone）
- month: 最后联系月份（jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec）
- day_of_week: 最后联系星期（mon, tue, wed, thu, fri）
- duration: 最后一次通话时长（秒）
- campaign: 本次活动联系次数
- pdays: 距上次联系天数（-1表示未联系过）
- previous: 之前活动联系次数
- poutcome: 之前营销结果（success, failure, other, unknown）
- y: 是否订阅定期存款（yes/no）- 这是目标变量

经济指标字段（新版数据）：
- emp_var_rate: 就业变动率
- cons_price_idx: 消费者物价指数
- cons_conf_idx: 消费者信心指数
- euribor3m: 3个月期欧元银行间利率
- nr_employed: 就业人数
"""


# ========== 意图识别 Prompt ==========
INTENT_CLASSIFICATION_PROMPT = """你是一个智能意图识别助手。请分析用户输入，判断其意图类型。

## 意图类型说明

1. **query** - 数据查询请求
   - 特征：询问具体数据、记录、明细
   - 示例关键词："查询"、"显示"、"列出"、"多少"、"有哪些"
   - 例：查询30岁以下的客户、显示所有学生职业的人

2. **stats** - 统计分析请求
   - 特征：需要计算统计指标、汇总数据
   - 示例关键词："统计"、"平均"、"总计"、"分布"、"占比"
   - 例：统计各职业的平均年龄、计算转化率

3. **viz** - 可视化请求
   - 特征：明确要求图表展示
   - 示例关键词："画图"、"图表"、"柱状图"、"饼图"、"趋势图"
   - 例：画出年龄分布图、用柱状图展示各职业转化率

4. **rag** - 知识问答请求
   - 特征：询问银行业务知识、概念解释、政策法规
   - 示例关键词："什么是"、"如何"、"为什么"、"解释"
   - 例：什么是KYC、定期存款和活期的区别

5. **chat** - 普通聊天
   - 特征：问候、寒暄、与数据无关的对话
   - 例：你好、谢谢、再见

## 混合意图处理规则

当用户请求包含多个意图时，按优先级选择：
- 如果要求"画图/图表" → viz
- 如果要求"统计/分析" → stats
- 如果要查询具体数据 → query
- 如果是知识性问题 → rag

## 输出格式

请只返回JSON格式：
```json
{{"intent": "意图类型", "confidence": 0.9, "reasoning": "判断理由"}}
```

confidence是置信度(0-1)，reasoning简要说明判断依据。
"""


# ========== Few-Shot 示例：Text-to-SQL ==========
TEXT_TO_SQL_EXAMPLES = """
## Few-Shot 示例

### 示例 1：简单条件查询
用户：查询30岁以下的客户
```sql
SELECT * FROM marketing_data WHERE age < 30 LIMIT 100;
```

### 示例 2：多条件查询
用户：显示已婚且有住房贷款的客户
```sql
SELECT * FROM marketing_data WHERE marital = 'married' AND housing = 'yes' LIMIT 100;
```

### 示例 3：分组统计
用户：统计各职业的客户数量
```sql
SELECT job, COUNT(*) as count FROM marketing_data GROUP BY job ORDER BY count DESC;
```

### 示例 4：转化率计算
用户：按教育程度统计转化率
```sql
SELECT
    education,
    COUNT(*) as total,
    SUM(CASE WHEN y = 'yes' THEN 1 ELSE 0 END) as converted,
    ROUND(100.0 * SUM(CASE WHEN y = 'yes' THEN 1 ELSE 0 END) / COUNT(*), 2) as conversion_rate
FROM marketing_data
GROUP BY education
ORDER BY conversion_rate DESC;
```

### 示例 5：范围查询
用户：查询通话时长超过5分钟的客户
```sql
SELECT * FROM marketing_data WHERE duration > 300 LIMIT 100;
```

### 示例 6：排序查询
用户：按余额从高到低显示客户
```sql
SELECT * FROM marketing_data WHERE balance IS NOT NULL ORDER BY balance DESC LIMIT 100;
```

### 示例 7：日期相关查询
用户：查询5月份联系的客户
```sql
SELECT * FROM marketing_data WHERE month = 'may' LIMIT 100;
```

### 示例 8：复杂聚合
用户：统计每个职业的平均年龄和平均余额
```sql
SELECT
    job,
    ROUND(AVG(age), 2) as avg_age,
    ROUND(AVG(balance), 2) as avg_balance
FROM marketing_data
GROUP BY job;
```

### 示例 9：NOT 条件
用户：查询没有个人贷款的客户
```sql
SELECT * FROM marketing_data WHERE loan = 'no' LIMIT 100;
```

### 示例 10：IN 子句
用户：查询职业是学生或退休人员的客户
```sql
SELECT * FROM marketing_data WHERE job IN ('student', 'retired') LIMIT 100;
```
"""


# ========== Text-to-SQL 主 Prompt ==========
TEXT_TO_SQL_PROMPT = """你是一个SQL生成专家。请将用户的自然语言转换为PostgreSQL查询语句。

## 数据库结构

{schema}

## 生成规则

1. **只生成 SELECT 语句**，禁止 DELETE/UPDATE/DROP/INSERT/TRUNCATE/ALTER/CREATE
2. **默认添加 LIMIT 100** 防止返回过多数据
3. **使用精确的字段名**，参考上面的数据库结构
4. **字符串值用单引号**，如 `marital = 'married'`
5. **处理 NULL 值**：使用 `IS NULL` 或 `IS NOT NULL`
6. **日期/月份字段**：month 的值是小写缩写（jan, feb, mar...）
7. **聚合查询**：使用 GROUP BY 时，所有非聚合字段都要加入
8. **转化率计算**：目标字段是 `y`，值为 'yes' 表示转化

## 常见模式

### 条件查询
```sql
SELECT * FROM marketing_data WHERE <条件> LIMIT 100;
```

### 分组统计
```sql
SELECT <分组列>, COUNT(*) as count FROM marketing_data GROUP BY <分组列>;
```

### 转化率
```sql
SELECT
    <分组列>,
    COUNT(*) as total,
    SUM(CASE WHEN y = 'yes' THEN 1 ELSE 0 END) as converted,
    ROUND(100.0 * SUM(CASE WHEN y = 'yes' THEN 1 ELSE 0 END) / COUNT(*), 2) as rate
FROM marketing_data
GROUP BY <分组列>;
```

## Few-Shot 示例

{examples}

## 注意事项

- 只输出SQL语句，不要任何解释
- 不要使用 markdown 代码块标记（```sql）
- 如果用户的问题模糊，生成最合理的查询
- 如果涉及不存在的字段，生成最接近的替代查询

现在请生成SQL：

用户问题：{user_input}

生成的SQL："""


# ========== SQL 修正 Prompt ==========
SQL_CORRECTION_PROMPT = """你是一个SQL修正专家。请分析以下错误信息并修正SQL语句。

## 原始SQL

{sql}

## 错误信息

{error}

## 数据库结构

{schema}

## 修正指南

1. **列不存在错误**：检查列名拼写，参考数据库结构使用正确的列名
2. **语法错误**：检查括号匹配、引号配对、逗号位置
3. **类型错误**：字符串比较要用单引号，数字不要引号
4. **GROUP BY 错误**：所有 SELECT 中的非聚合列必须出现在 GROUP BY 中
5. **表名错误**：确保使用正确的表名 `marketing_data`
6. **函数错误**：PostgreSQL 函数名检查，如 ROUND()、SUM()、COUNT()

## 修正要求

1. 只输出修正后的SQL语句
2. 不要任何解释或注释
3. 不要使用 markdown 代码块标记
4. 确保是合法的 SELECT 语句

修正后的SQL："""


# ========== 最终答案生成 Prompt（带上下文）==========
GENERATE_ANSWER_WITH_CONTEXT_PROMPT = """你是银行营销数据分析助手 Z-Rop。请根据工作流执行结果生成用户友好的回答。

## 用户原始问题

{user_input}

## 对话历史（最近几轮）

{chat_history}

## 执行结果

{execution_result}

## 回答要求

1. **使用简洁明了的中文**
2. **如果有数据结果**：
   - 总结关键发现（不要列出所有数据）
   - 突出有价值的洞察
   - 如果数据量大，只展示前几条示例
3. **如果有图表**：简要说明图表展示的内容
4. **如果有SQL**：说明执行的查询类型，无需展示完整SQL
5. **如果出错**：提供友好的错误说明和建议
6. **利用上下文**：如果用户有追问（如"为什么"、"分析一下"），结合之前的结果回答
7. **专业且亲切**：使用专业术语但保持亲和力

## 回答格式

- 使用段落式回答，不要用列表罗列数据
- 适当使用加粗强调关键数字
- 如果需要展示表格，用简洁的markdown表格

请生成回答："""


# ========== 上下文增强 Prompt ==========
CONTEXT_ENHANCED_USER_INPUT = """## 用户问题

{user_input}

## 对话上下文

{chat_context}

---

请结合对话上下文，判断：
1. 用户是否有指代词（"它"、"那些"、"这个"等）需要消解？
2. 用户是否在追问之前的结果（"为什么"、"分析一下"、"详细说明"）？

**消解后的完整问题**：
（如果原问题完整清晰，则保持不变；如果有指代，补全为完整问题）"""


# ========== RAG 问答 Prompt（优化版）==========
RAG_ANSWER_PROMPT = """你是银行智能助手 Z-Rop，专门回答银行业务和金融知识相关问题。

## 用户问题

{question}

## 检索到的知识文档

{context}

## 对话历史

{chat_history}

## 回答要求

1. **优先使用知识文档内容**：基于检索到的文档回答
2. **标注来源**：引用文档时说明"根据XX文档"
3. **诚实原则**：如果文档中没有答案，明确告知用户
4. **结合上下文**：如果用户有追问，参考对话历史
5. **专业清晰**：使用专业但易懂的语言
6. **结构化回答**：适当使用分点说明

请生成回答："""


# ========== 意图识别的 Few-Shot 示例 ==========
INTENT_FEW_SHOT_EXAMPLES = {
    "query": [
        "查询30岁以下的客户",
        "显示所有学生职业的人",
        "列出余额大于5000的客户",
        "有多少客户有住房贷款",
        "查询5月份联系的所有客户"
    ],
    "stats": [
        "统计各职业的客户数量",
        "计算平均年龄",
        "按教育程度统计转化率",
        "分析通话时长的分布情况",
        "计算整体转化率"
    ],
    "viz": [
        "画出年龄分布图",
        "用柱状图展示各职业转化率",
        "画出余额趋势图",
        "生成一个饼图显示婚姻状况分布",
        "可视化通话时长分布"
    ],
    "rag": [
        "什么是KYC认证",
        "定期存款和活期存款有什么区别",
        "银行的反洗钱规定是什么",
        "解释一下什么是理财产品",
        "信用卡逾期有什么后果"
    ],
    "chat": [
        "你好",
        "谢谢",
        "再见",
        "你能帮我做什么",
        "你叫什么名字"
    ]
}


def get_intent_classification_prompt_with_examples() -> str:
    """获取带 Few-Shot 示例的意图识别 Prompt"""

    examples_str = "\n## Few-Shot 示例\n\n"

    for intent, examples in INTENT_FEW_SHOT_EXAMPLES.items():
        examples_str += f"### {intent.upper()} 意图\n"
        for ex in examples:
            examples_str += f"- \"{ex}\"\n"
        examples_str += "\n"

    return INTENT_CLASSIFICATION_PROMPT + "\n" + examples_str


def build_context_string(chat_history: list, max_turns: int = 3) -> str:
    """
    构建对话上下文字符串

    Args:
        chat_history: 聊天历史列表
        max_turns: 最多包含的历史轮数

    Returns:
        格式化的上下文字符串
    """
    if not chat_history:
        return "（无对话历史）"

    # 只取最近的几轮对话
    recent_history = chat_history[-max_turns:] if len(chat_history) > max_turns else chat_history

    context_parts = []
    for i, turn in enumerate(recent_history, 1):
        if isinstance(turn, dict):
            user_msg = turn.get("user", turn.get("question", ""))
            assistant_msg = turn.get("assistant", turn.get("answer", ""))
            context_parts.append(f"第{i}轮：\n  用户：{user_msg}\n  助手：{assistant_msg[:100]}...")
        else:
            context_parts.append(f"第{i}轮：{str(turn)[:100]}")

    return "\n".join(context_parts)


def resolve_coreference(user_input: str, chat_history: list) -> str:
    """
    指代消解：将用户输入中的指代词替换为实际内容

    Args:
        user_input: 当前用户输入
        chat_history: 聊天历史

    Returns:
        消解后的完整问题
    """
    # 简单的指代词列表
    pronouns = ["它", "它们", "那些", "这个", "这些", "他", "她", "他们"]

    # 检查是否包含指代词
    has_pronoun = any(p in user_input for p in pronouns)

    if not has_pronoun or not chat_history:
        return user_input

    # 获取上一轮的问题
    last_question = ""
    if chat_history:
        last_turn = chat_history[-1]
        if isinstance(last_turn, dict):
            last_question = last_turn.get("user", last_turn.get("question", ""))
        else:
            last_question = str(last_turn)

    if not last_question:
        return user_input

    # 简单的替换规则（实际应该用 LLM 做更智能的消解）
    resolved = user_input
    for pronoun in pronouns:
        if pronoun in resolved:
            # 指代当前讨论的主题（上轮问题的主语）
            # 这里是简化处理，实际应该更复杂
            resolved = resolved.replace(pronoun, f"之前查询的{last_question[:10]}")
            break

    return resolved
