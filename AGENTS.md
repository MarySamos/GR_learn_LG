# BankAgent-Pro 项目备忘录

## 设计风格规范（2026年3月更新）

### 整体风格
- **风格定位**：现代极简 + 玻璃质感 + 圆润设计
- **参考风格**：类似 Obsidian/Notion 的轻量级设计

### 配色方案（禁止使用蓝色和紫色）
```css
/* 主色调 - 浅粉色系 */
--color-primary: #ff6b81;
--color-primary-light: #ff8fa3;
--color-primary-dark: #e8556e;

/* 中性色 */
--color-text-primary: #333333;
--color-text-regular: #666666;
--color-text-secondary: #999999;
--color-text-placeholder: #cccccc;

/* 背景色 */
--color-bg-page: #f8f8f8;
--color-bg-container: #ffffff;

/* 边框色 */
--color-border: #e0e0e0;
--color-border-light: #eeeeee;
```

### 色彩使用规范
- **卡片图标颜色**：
  - Rose（粉色系）: `#ff6b81` - 用于主要强调
  - Green: `#52c41a` - 用于成功/正向
  - Orange: `#faad14` - 用于警告/中性
  - Blue: `#52a8ff` - 仅用于数据展示（不作为主色）
- **禁止使用**：紫色、深蓝色作为主色

### 圆角规范
```css
--radius-small: 6px;   /* 小元素 */
--radius-base: 8px;    /* 基础元素 */
--radius-large: 12px;  /* 大卡片 */
```

### 阴影规范
```css
--shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.02);
--shadow-light: 0 2px 8px rgba(0, 0, 0, 0.04);
--shadow-base: 0 4px 12px rgba(0, 0, 0, 0.05);
--shadow-dark: 0 8px 24px rgba(0, 0, 0, 0.08);
```

---

## 前端图标导入问题

### 问题描述
Element Plus Icons 中某些图标名称不存在，导致导入错误。

### 解决方法
1. 检查 Element Plus Icons 中实际存在的图标：
   ```bash
   grep "export.*IconName" frontend/node_modules/@element-plus/icons-vue/dist/types/components/index.d.ts
   ```

2. **常用图标对照表**（存在 vs 不存在）：

   | 需要的效果 | 正确的图标名称 | 错误的名称 |
   |-----------|---------------|-----------|
   | 向上箭头 | `CaretTop`, `ArrowUp` | ~~`TrendUp`~~ |
   | 向下箭头 | `CaretBottom`, `ArrowDown` | ~~`TrendDown`~~ |
   | 图表 | `TrendCharts` | - |
   | 用户 | `User` | - |
   | 锁 | `Lock` | - |
   | 聊天 | `ChatDotRound` | - |
   | 数据分析 | `DataAnalysis` | - |
   | 刷新 | `Refresh` | - |
   | 钱/余额 | `Money` | - |
   | 电话 | `Phone` | - |
   | 文档 | `Document` | - |
   | 网格 | `Grid` | - |
   | 搜索 | `Search` | - |
   | 下载 | `Download` | - |
   | 删除 | `Delete` | - |
   | 发送 | `Promotion` | - |
   | 切换 | `SwitchButton` | - |
   | 银行 | ~~`Bank`~~ 不存在，用 `TrendCharts` 代替 |

### 项目目录结构
- `frontend/` - 前端 Vue3 + Vite 项目
- `backend/` - 后端 Python/FastAPI 项目
- 前端端口: 5173
- 后端端口: 8002

### 启动命令
```bash
# 前端
cd frontend && npm run dev

# 后端
cd backend && python main.py
```
