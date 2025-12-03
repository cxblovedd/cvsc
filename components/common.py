import streamlit as st
from database.queries import get_dashboard_stats
from auth.login import logout

def render_sidebar():
    """渲染侧边栏"""
    st.sidebar.title("🏥 CVSC 管理平台")
    st.sidebar.markdown("---")
    
    # 用户信息显示
    if st.session_state.get('logged_in'):
        st.sidebar.markdown(f"**👤 当前用户**: {st.session_state.get('username', 'Unknown')}")
        if st.sidebar.button("🚪 退出登录", use_container_width=True):
            logout()
            st.rerun()
        st.sidebar.markdown("---")

def render_navigation_menu():
    """渲染导航菜单"""
    return st.sidebar.radio(
        "功能导航",
        ["📊 实时监控看板", "📈 患者数据分析", "⚙️ 设备管理", "🔌 字段映射", "📋 系统日志"],
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