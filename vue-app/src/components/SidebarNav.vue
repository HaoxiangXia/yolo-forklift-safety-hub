<template>
  <nav class="sidebar glass">
    <!-- 顶部 Logo -->
    <div class="sidebar-header">
      <div class="brand">
        <img src="/logo.png" alt="智盾" class="brand-logo" />
        <span class="brand-name">智盾</span>
      </div>
    </div>

    <!-- 中间导航列表 -->
    <div class="sidebar-nav">
      <router-link v-for="item in menuItems" :key="item.path" :to="item.path" class="nav-item" active-class="active">
        <span class="nav-icon" v-html="item.icon"></span>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </div>

    <!-- 底部用户信息 -->
    <div class="sidebar-footer">
      <div class="user-info">
        <div class="user-avatar">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/>
          </svg>
        </div>
        <div class="user-details">
          <span class="user-name">管理员</span>
          <span class="user-role">System Admin</span>
        </div>
      </div>
      <button class="logout-btn" @click="handleLogout">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
          <polyline points="16 17 21 12 16 7"/>
          <line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
        <span>退出登录</span>
      </button>
    </div>
  </nav>
</template>

<script setup>
const menuItems = [
  {
    path: '/',
    label: '仪表盘',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>`
  },
  {
    path: '/devices',
    label: '设备列表',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="6" width="20" height="12" rx="2"/>
      <path d="M6 12h4m4 0h4"/>
      <circle cx="18" cy="6" r="1" fill="currentColor"/>
    </svg>`
  },
  {
    path: '/logs',
    label: '业务日志',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
      <path d="M14 2v6h6"/>
      <path d="M8 13h8m-8 4h4"/>
    </svg>`
  },
    {
    path: '/trend',   // ✅ 新增（就这一块）
    label: '趋势分析',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="3 17 9 11 13 15 21 7"/>
      <polyline points="14 7 21 7 21 14"/>
    </svg>`
  },
   {
    path: '/history',
    label: '报警历史',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M3 12h18"/>
      <path d="M3 6h18"/>
      <path d="M3 18h18"/>
    </svg>`
  }
]

const handleLogout = () => {
  console.log('退出登录')
}
</script>

<style scoped>
.sidebar {
  width: 220px;
  flex-shrink: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  border-radius: 0 24px 24px 0;
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: none;
  border-right: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow:
    0 8px 32px rgba(140, 120, 180, 0.10),
    inset 0 1px 0 rgba(255, 255, 255, 0.35);
  font-family: 'DM Sans', sans-serif;
}

.sidebar-header {
  padding: 0 24px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-logo {
  width: 36px;
  height: 36px;
  object-fit: contain;
  border-radius: 10px;
}

.brand-name {
  font-family: 'Outfit', sans-serif;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #3a3550;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-radius: 16px;
  color: #8a8aa8;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #5c5678;
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.25);
  color: #3a3550;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  flex-shrink: 0;
  transition: background 0.25s ease;
}

.nav-item:hover .nav-icon {
  background: rgba(255, 255, 255, 0.18);
}

.nav-item.active .nav-icon {
  background: rgba(255, 255, 255, 0.22);
}

.nav-icon :deep(svg) {
  width: 16px;
  height: 16px;
}

.sidebar-footer {
  padding: 16px 14px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.user-avatar {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(140, 120, 180, 0.15);
  color: #5c5678;
  flex-shrink: 0;
}

.user-avatar svg {
  width: 18px;
  height: 18px;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: #3a3550;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 11px;
  color: #8a8aa8;
  letter-spacing: 0.02em;
}

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 11px 16px;
  border: none;
  border-radius: 12px;
  background: rgba(255, 59, 48, 0.08);
  color: #c45c55;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid rgba(255, 59, 48, 0.12);
}

.logout-btn:hover {
  background: rgba(255, 59, 48, 0.14);
  color: #ff3b30;
  border-color: rgba(255, 59, 48, 0.2);
}

.logout-btn svg {
  width: 16px;
  height: 16px;
}
</style>
