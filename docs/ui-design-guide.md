# 叉车作业人车互斥报警系统 - UI 设计规范

本文档定义了系统的视觉设计标准，确保所有页面保持一致的 Apple 工业风格。

---

## 一、设计理念

- **极简**：去除冗余装饰
- **高级**：企业级监控系统质感
- **克制**：避免过度设计
- **工业感**：专业、严谨、可信

---

## 二、视觉规范

### 1. 颜色体系

```css
:root {
  /* 背景 */
  --bg-primary: #f5f5f7;      /* 页面背景 */
  --bg-card: #ffffff;         /* 卡片背景 */

  /* 文字 */
  --text-primary: #1d1d1f;    /* 主文字 */
  --text-secondary: #6e6e73;  /* 次级文字 */

  /* 边框 */
  --border-color: #d2d2d7;    /* 边框线 */

  /* 状态颜色 */
  --status-normal: #34c759;   /* 正常 - 绿色 */
  --status-alarm: #ff3b30;    /* 报警 - 红色 */
  --status-offline: #8e8e93;  /* 离线 - 灰色 */

  /* 圆角 */
  --radius: 6px;

  /* 字体 */
  --font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
}
```

### 2. 禁止使用

- ❌ emoji
- ❌ 渐变色
- ❌ 大圆角（> 6px）
- ❌ 卡通图标
- ❌ 彩色阴影
- ❌ 花哨动画
- ❌ PNG 图标
- ❌ IconFont

### 3. 圆角限制

```css
/* 允许 */
border-radius: 4px;
border-radius: 6px;

/* 禁止 */
border-radius: 20px;
border-radius: 50%;
border-radius: 999px;
```

---

## 三、布局规范

### 1. 页面容器

```css
.page-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}
```

### 2. 模块间距

```css
gap: 24px;
margin-bottom: 24px;
```

### 3. 通用卡片结构

```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}
```

### 4. 头部布局

```html
<div class="header">
  <div class="header-left">
    <div class="header-title">
      <h1>页面主标题</h1>
      <div class="subtitle">副标题说明</div>
    </div>
  </div>
  <div class="nav-bar">
    <a href="/path" class="nav-btn">导航按钮</a>
  </div>
</div>
```

```css
.header {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 20px 24px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-title h1 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-title .subtitle {
  font-size: 13px;
  color: var(--text-secondary);
}
```

---

## 四、组件规范

### 1. 导航按钮

```css
.nav-bar {
  display: flex;
  gap: 8px;
}

.nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--bg-card);
  color: var(--text-primary);
  text-decoration: none;
  border-radius: var(--radius);
  border: 1px solid var(--border-color);
  font-size: 13px;
  font-weight: 400;
  transition: all 0.2s ease;
}

.nav-btn:hover {
  background: var(--bg-primary);
  border-color: var(--text-secondary);
}

.nav-btn svg {
  width: 14px;
  height: 14px;
}
```

### 2. 状态指示器

```html
<span class="status-indicator">
  <span class="status-dot normal"></span>
  <span class="status-text normal">正常</span>
</span>
```

```css
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.normal { background: var(--status-normal); }
.status-dot.alarm { background: var(--status-alarm); }
.status-dot.offline { background: var(--status-offline); }

.status-text.normal { color: var(--status-normal); }
.status-text.alarm { color: var(--status-alarm); }
.status-text.offline { color: var(--status-offline); }
```

### 3. 数据表格

```css
.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-primary);
}

.data-table td {
  padding: 14px 16px;
  font-size: 14px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}

.data-table tbody tr {
  transition: background-color 0.15s ease;
}

.data-table tbody tr:hover {
  background: var(--bg-primary);
}
```

### 4. 按钮

```css
.img-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.img-btn:hover {
  background: var(--text-primary);
  color: var(--bg-card);
  border-color: var(--text-primary);
}
```

### 5. 弹窗

```css
.modal {
  display: none;
  position: fixed;
  z-index: 1000;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal-content {
  background-color: var(--bg-card);
  margin: 5% auto;
  padding: 0;
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  width: 90%;
  max-width: 800px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  border-radius: var(--radius);
  color: var(--text-secondary);
  transition: all 0.15s ease;
}

.modal-close:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}
```

---

## 五、SVG 图标规范

### 1. 图标风格

- 极简
- 线性
- 单色
- 工业风

### 2. 图标示例

```html
<!-- 监控图标 -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
  <path d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
  <path d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"/>
</svg>

<!-- 地图图标 -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
  <path d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
</svg>

<!-- 日志图标 -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
  <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
</svg>

<!-- 设备图标 -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
  <path d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
</svg>

<!-- 搜索图标 -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
</svg>

<!-- 刷新图标 -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
</svg>

<!-- 关闭图标 -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M6 18L18 6M6 6l12 12"/>
</svg>

<!-- 图片图标 -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
  <path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
</svg>
```

---

## 六、文字规范

### 1. 标题

```css
h1 {
  font-size: 24px;
  font-weight: 600;
}

h2 {
  font-size: 18px;
  font-weight: 600;
}

h3 {
  font-size: 16px;
  font-weight: 600;
}
```

### 2. 正文

```css
body {
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
}
```

### 3. 次级文字

```css
.subtitle, .time-col {
  font-size: 13px;
  color: var(--text-secondary);
}
```

---

## 七、页面模板

### 基础结构

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>页面标题 - 叉车作业人车互斥报警系统</title>
  <style>
    /* 引入 CSS 变量和基础样式 */
  </style>
</head>
<body>
  <div class="page-container">
    <!-- 头部 -->
    <div class="header">
      <div class="header-left">
        <div class="header-title">
          <h1>页面主标题</h1>
          <div class="subtitle">副标题说明</div>
        </div>
      </div>
      <div class="nav-bar">
        <a href="/" class="nav-btn">
          <svg>...</svg>
          导航
        </a>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="card">
      <div class="card-header">
        <svg>...</svg>
        <span class="card-title">卡片标题</span>
      </div>
      <!-- 内容 -->
    </div>
  </div>
</body>
</html>
```

---

## 八、状态文字对照表

| 英文 | 中文 |
|------|------|
| Normal | 正常 |
| Alarm | 报警 |
| Offline | 离线 |
| Loading... | 加载中... |
| No data | 暂无数据 |
| Device ID | 设备ID |
| Status | 状态 |
| Last Update | 最后更新 |
| Time | 时间 |
| Device | 设备 |
| Zone | 区域 |
| Image | 图片 |
| View | 查看 |
| Factory Floor Map | 工厂平面图 |
| Device Status | 设备状态 |
| Recent Alarms | 最近报警 |
| Alarm Snapshot | 报警截图 |

---

## 九、路由规范

| 路径 | 页面 | 模板文件 |
|------|------|----------|
| `/` | 实时监控 | dashboard.html |
| `/devices` | 设备列表 | devices.html |
| `/logs` | 业务日志 | logs.html |

---

## 十、检查清单

新建页面时，确保：

- [ ] 使用 CSS 变量定义颜色
- [ ] 背景色为 `#f5f5f7`
- [ ] 卡片为白色背景 + 细边框
- [ ] 圆角为 `6px`
- [ ] 使用 SVG 图标（禁止 emoji）
- [ ] 字体使用系统字体栈
- [ ] 头部布局使用 header-left + header-title
- [ ] 表格使用统一样式
- [ ] 所有文字使用中文
- [ ] 状态颜色符合规范