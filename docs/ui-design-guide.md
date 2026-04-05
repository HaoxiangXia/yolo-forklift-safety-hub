# UI 设计指南 - 智盾叉车安全监控系统

## 设计理念

**美学方向**: 精致毛玻璃 × 静态极光渐变

界面将磨砂玻璃面板与静态极光渐变背景融合，设计语言**简约而富有氛围感**——干净的卡片布局悬浮于柔和的极光渐变之上，在不干扰内容的前提下营造深度与视觉层次。

**核心原则**:
- **层次深度**: 多层径向渐变模糊色块营造极光氛围
- **玻璃清晰**: 磨砂玻璃面板提供结构感，同时保持与背景的视觉连通
- **克制动效**: 仅保留必要的页面过渡和微交互，背景保持静态
- **字体层级**: 三款精心挑选的字体构建清晰的视觉层次

---

## 字体系统

### 字体栈

| 角色 | 字体 | 字重 | 用途 |
|------|------|------|------|
| **展示** | Outfit | 300, 400, 500, 600, 700 | 标题、KPI 数字、卡片标题 |
| **正文** | DM Sans | 300, 400, 500, 600 | 正文、标签、描述 |
| **等宽** | JetBrains Mono | 400, 500 | 设备ID、时间戳、技术数据 |

### 选型理由

- **Outfit**: 几何无衬线字体，字形独特。比 Inter 更精致，比 Poppins 更现代。干净的几何感与玻璃美学完美契合。
- **DM Sans**: 低对比度人文主义无衬线，小字号下可读性极佳。比系统字体更有温度、更有辨识度。
- **JetBrains Mono**: 面向开发者的等宽字体，为设备ID和时间戳带来技术可信度。

### 使用规范

```css
/* 标题和展示文字 */
font-family: 'Outfit', sans-serif;

/* 正文和 UI 文字 */
font-family: 'DM Sans', sans-serif;

/* 设备ID、时间戳、技术数据 */
font-family: 'JetBrains Mono', monospace;
```

---

## 色彩系统

### 基础色板

| 变量 | 色值 | 用途 |
|------|------|------|
| 背景基色 | `#e8e6f0` | 页面底色 |
| 主文字 | `#3a3550` | 标题、主要文字 |
| 次要文字 | `#5c5678` | 正文 |
| 弱化文字 | `#8a8aa8` | 标签、元信息 |

### 状态色

| 状态 | 色值 | 用途 |
|------|------|------|
| 正常 | `#34c759` | 在线、健康 |
| 报警 | `#ff3b30` | 活跃报警、警告 |
| 离线 | `#b0a8c8` | 离线设备 |
| 信息 | `#2d8a4e` | 信息徽章 |
| 警告 | `#a67c00` | 警告徽章 |

### 极光色板

极光背景使用精心编排的渐变调色板：

| 层级 | 渐变 | 用途 |
|------|------|------|
| 色带 1 | `#1e3a8a` (55%) | 深靛蓝基底 |
| 色带 2 | `#581c87` (45%) | 紫色次层 |
| 色带 3 | `#2563eb` (50%) | 蓝色点缀 |
| 色带 4 | `#7e22ce` (40%) | 紫色高光 |

### 毛玻璃面板公式

```css
background: rgba(255, 255, 255, 0.18);
backdrop-filter: blur(16px);
-webkit-backdrop-filter: blur(16px);
border: 1px solid rgba(255, 255, 255, 0.3);
box-shadow:
  0 8px 32px rgba(140, 120, 180, 0.10),
  inset 0 1px 0 rgba(255, 255, 255, 0.35);
```

---

## 极光背景系统

### 架构

极光背景组件 (`AuroraBackground.vue`) 作为共享组件应用于所有页面，采用**静态渐变**方案：

1. **渐变带层**: 4 个大型径向渐变模糊色块，固定位置，无动画

### 组件结构

```
aurora-canvas (fixed, 全屏)
└── aurora-bands (4 个静态色带)
    ├── band-1: 900×600, 左上, 靛蓝 radial-gradient
    ├── band-2: 1000×700, 右上, 紫色 radial-gradient
    ├── band-3: 700×500, 左下, 蓝色 radial-gradient
    └── band-4: 600×450, 居中, 紫色 radial-gradient
```

### 关键设计决策

- **`filter: blur(100px)`** 产生柔和极光效果
- **`radial-gradient`** 从中心向外衰减至透明
- **无动画**，保持静态氛围，减少视觉干扰
- **`pointer-events: none`** 确保不阻挡交互

---

## 布局系统

### 页面结构

```
┌─────────────────────────────────────────────────┐
│ AuroraBackground (fixed, 全屏固定)              │
├──────────┬──────────────────────────────────────┤
│ Sidebar  │ Main Content                         │
│ 220px    │ flex: 1, z-index: 1                  │
│          │  ┌────────────────────────────────┐  │
│          │  │ Page Header (glass card)       │  │
│          │  ├────────────────────────────────┤  │
│          │  │ Content Card (glass)           │  │
│          │  │  - 筛选栏                       │  │
│          │  │  - 数据表格 / 网格              │  │
│          │  │  - 分页                         │  │
│          │  └────────────────────────────────┘  │
└──────────┴──────────────────────────────────────┘
```

### 根布局 (App.vue)

```
app-container (flex, min-height: 100vh)
├── AuroraBackground (fixed, z-index: 0)
├── SidebarNav (220px, flex-shrink: 0)
└── main.main-content (flex: 1, min-width: 0)
    └── router-view (带 fade 过渡)
```

### 网格模式

**仪表盘网格**:
```css
grid-template-columns: 1fr 260px;
grid-template-areas:
  "map kpi"
  "chart kpi";
```

**筛选栏网格**:
```css
grid-template-columns: 160px 160px 200px auto;
```

### 响应式断点

| 断点 | 行为 |
|------|------|
| `> 1200px` | 完整多列布局 |
| `900-1200px` | 卡片堆叠，KPI 横向排列 |
| `< 900px` | 单列，筛选栏堆叠 |
| `< 768px` | 紧凑内边距，减小高度 |

---

## 侧边导航栏

### 结构

```
sidebar (220px, glass)
├── sidebar-brand
│   ├── logo.png (36×36px, rounded)
│   └── "智盾" (Outfit, 22px, 700)
└── sidebar-menu
    ├── 仪表盘 (router-link → /)
    ├── 设备列表 (router-link → /devices)
    └── 业务日志 (router-link → /logs)
```

### 样式特征

- 右侧圆角 `border-radius: 0 24px 24px 0`
- 右边框分隔 `border-right: 1px solid rgba(255, 255, 255, 0.25)`
- 菜单项圆角 `border-radius: 16px`
- 激活态: 白色半透明背景 + 内发光
- 图标容器: 28×28px 圆角方块

---

## 动效设计

### 页面过渡

```css
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.35s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
```

### 卡片悬停

卡片悬停时上浮并增强阴影：
```css
.card:hover {
  box-shadow: 0 16px 48px rgba(140, 120, 180, 0.18),
              inset 0 1px 0 rgba(255, 255, 255, 0.4);
  transform: translateY(-3px);
}
```

### 页面入场动画

页面内容使用 CSS 动画实现入场效果：
```css
.dashboard-grid {
  animation: grid-reveal 0.8s cubic-bezier(0.4, 0, 0.2, 1) both;
}

.content {
  animation: page-reveal 0.7s cubic-bezier(0.4, 0, 0.2, 1) both;
}

@keyframes grid-reveal {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes page-reveal {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### 微交互

| 元素 | 交互 | 效果 |
|------|------|------|
| 筛选按钮 | 悬停 | `translateY(-1px)` + 背景提亮 |
| 表格行 | 悬停 | 背景叠加 |
| 状态点(报警) | 持续 | 脉冲透明度 |
| 模态关闭按钮 | 悬停 | `rotate(90deg)` |
| 图片 | 悬停 | `scale(1.04)` + 阴影 |
| KPI 数值(报警) | 持续 | 脉冲 + 微缩放 |
| 图例点 | 常亮 | `box-shadow` 发光 |

---

## 组件规范

### 毛玻璃卡片

所有内容容器使用玻璃模式：
- 主卡片 `border-radius: 24px`，头部 `20px`
- `backdrop-filter: blur(16px)` 磨砂效果
- 白色边框 30% 不透明度定义边缘
- 内嵌顶部高光营造深度错觉

### 状态指示器

- **圆点**: 8px 圆形 + 彩色发光 (`box-shadow`)
- **报警点**: 额外脉冲动画
- **文字**: 与圆点同色，无背景徽章

### 徽章与标签

- 胶囊形状 (`border-radius: 999px`)
- 半透明背景 + 深色文字
- 标签文字大写 + 字间距

### 模态窗口

- 全屏遮罩 `backdrop-filter: blur(8px)`
- 内容卡片上滑 + 缩放进入
- 关闭按钮悬停旋转 90°
- 最大 90% 视口宽度，90vh 高度

### 自定义滚动条

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(140, 120, 180, 0.25);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(140, 120, 180, 0.4);
}
```

### 文字选中

```css
::selection {
  background: rgba(184, 169, 232, 0.3);
  color: #3a3550;
}
```

---

## 可访问性

- 所有交互元素有可见的悬停状态
- 玻璃背景上的文字对比度满足 WCAG AA
- 状态信息通过颜色 + 文字传达（不仅依赖颜色）
- 语义化 HTML 结构，正确的标题层级

---

## 文件结构

```
vue-app/src/
├── components/
│   ├── AuroraBackground.vue    # 共享极光背景（静态渐变）
│   ├── SidebarNav.vue          # 左侧导航栏（含logo）
│   ├── LineChart.vue           # ECharts 折线图封装
│   └── GlassCard.vue           # 可复用毛玻璃卡片
├── views/
│   ├── Dashboard.vue           # 仪表盘（地图 + KPI + 图表）
│   ├── Devices.vue             # 设备列表（筛选 + 详情模态）
│   └── Logs.vue                # 日志查询（分页）
├── App.vue                     # 根布局 + 全局样式
└── main.js                     # 应用入口
```

---

## 设计令牌 (CSS 变量)

推荐在后续扩展中使用以下 CSS 自定义属性：

```css
:root {
  /* 颜色 */
  --color-bg: #e8e6f0;
  --color-text: #3a3550;
  --color-text-secondary: #5c5678;
  --color-text-muted: #8a8aa8;
  --color-status-normal: #34c759;
  --color-status-alarm: #ff3b30;
  --color-status-offline: #b0a8c8;

  /* 毛玻璃 */
  --glass-bg: rgba(255, 255, 255, 0.18);
  --glass-blur: 16px;
  --glass-border: rgba(255, 255, 255, 0.3);
  --glass-radius: 24px;

  /* 字体 */
  --font-display: 'Outfit', sans-serif;
  --font-body: 'DM Sans', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* 动效 */
  --ease-out: cubic-bezier(0.4, 0, 0.2, 1);
  --duration-fast: 0.15s;
  --duration-normal: 0.25s;
  --duration-slow: 0.35s;
}
```

---

## 各页面特殊样式

### 仪表盘 (Dashboard.vue)

- KPI 数值使用 48px Outfit 700 字重
- KPI 报警值带文字发光 + 脉冲动画
- 地图图例圆点带 `box-shadow` 发光效果
- 网格布局: 地图占主区域，KPI 纵向排列在右侧

### 设备列表 (Devices.vue)

- 设备ID 使用 JetBrains Mono 等宽字体
- 报警状态点带脉冲动画 (`dot-pulse` keyframes)
- WebSocket 连接状态点带绿色发光
- 详情模态带滑入动画 (`modal-slide-in`)
- 图片悬停放大 + 阴影增强

### 业务日志 (Logs.vue)

- 日志级别徽章使用 Outfit 字体 + 大写 + 字间距
- 时间列使用 JetBrains Mono + `white-space: nowrap`
- 分页按钮悬停上浮效果
