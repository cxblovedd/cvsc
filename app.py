import streamlit as st
import logging
from database.connection import test_connection
from auth.login import check_authentication
from components.common import render_sidebar, render_navigation_menu, render_sidebar_stats
from modules.dashboard_page import render_dashboard
from modules.patient_search_page import render_patient_search
from modules.device_management_page import render_device_management
from modules.field_mapping_page import render_field_mapping
from modules.system_logs_page import render_system_logs
from config import config

# ================= 配置与初始化 =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """主应用入口"""
    # 设置页面配置（只在主应用中设置一次）
    st.set_page_config(
        page_title=config.PAGE_TITLE,
        layout=config.PAGE_LAYOUT,
        page_icon=config.PAGE_ICON,
        initial_sidebar_state="expanded"
    )
    
    # 检查用户认证
    if not check_authentication():
        return
    
    # 测试数据库连接
    try:
        if not test_connection():
            st.error("❌ 数据库连接失败，请检查配置")
            st.stop()
    except Exception as e:
        st.error(f"❌ 数据库连接异常: {e}")
        st.stop()
    
    # 渲染侧边栏（包含用户信息和退出按钮）
    render_sidebar()
    
    # 渲染导航菜单和统计信息
    menu = render_navigation_menu()
    render_sidebar_stats()
    
    # 根据选择渲染对应页面
    if menu == "📊 实时监控看板":
        render_dashboard()
    elif menu == "🔍 患者检索分析":
        render_patient_search()
    elif menu == "⚙️ 设备管理":
        render_device_management()
    elif menu == "🔌 字段映射":
        render_field_mapping()
    elif menu == "📋 系统日志":
        render_system_logs()

if __name__ == "__main__":
    main()