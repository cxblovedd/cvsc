import streamlit as st
from database.queries import get_dashboard_stats
from auth.login import logout, has_permission

def render_sidebar():
    """渲染侧边栏"""
    st.sidebar.title("🏥 CVSC 管理平台")
    st.sidebar.markdown("---")
    
    # 用户信息显示
    if st.session_state.get('logged_in'):
        role_display = {
            "admin": "系统管理员",
            "medical_staff": "医护人员", 
            "technical_staff": "技术人员",
            "guest": "访客"
        }
        user_role = st.session_state.get('user_role', 'guest')
        st.sidebar.markdown(f"**👤 当前用户**: {st.session_state.get('username', 'Unknown')}")
        st.sidebar.markdown(f"**🔖 用户角色**: {role_display.get(user_role, '未知')}")
        if st.sidebar.button("🚪 退出登录", use_container_width=True):
            logout()
            st.rerun()
        st.sidebar.markdown("---")

def render_navigation_menu():
    """渲染导航菜单（基于权限）"""
    menu_options = []
    
    # 调试信息
    user_role = st.session_state.get('user_role', 'unknown')
    user_permissions = st.session_state.get('user_permissions', [])
    
    # 根据用户权限动态生成菜单
    if has_permission("dashboard"):
        menu_options.append("📊 实时监控看板")
    if has_permission("search"):
        menu_options.append("🔍 患者检索分析")
    if has_permission("device_management"):
        menu_options.append("⚙️ 设备管理")
    if has_permission("field_mapping"):
        menu_options.append("🔌 字段映射")
    if has_permission("system_logs"):
        menu_options.append("📋 系统日志")
    
    # 调试信息（可以在开发时启用）
    if st.sidebar.checkbox("显示权限调试信息", key="show_debug"):
        st.sidebar.write(f"用户角色: {user_role}")
        st.sidebar.write(f"用户权限: {user_permissions}")
        st.sidebar.write(f"可用菜单: {menu_options}")
    
    if not menu_options:
        st.error("您没有访问任何功能的权限")
        return None
    
    return st.sidebar.radio(
        "功能导航",
        menu_options,
        label_visibility="collapsed",
        key="main_navigation"
    )

def render_sidebar_stats():
    """渲染侧边栏统计信息"""
    st.sidebar.markdown("---")
    st.sidebar.caption("系统概览")
    try:
        stats = get_dashboard_stats()
        st.sidebar.metric("📝 今日采集", f"{stats['today_collections']}")
        st.sidebar.metric("🖥️ 在线设备", f"{stats['online_devices']}")
    except:
        pass

def render_footer():
    """渲染页脚"""
    st.divider()
    from datetime import datetime
    st.caption(f"Build: {datetime.now().strftime('%Y-%m-%d')} | Supported by IT Dept.")