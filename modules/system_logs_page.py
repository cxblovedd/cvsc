import streamlit as st
from database.queries import get_system_logs
from components.common import render_footer

def render_system_logs():
    """渲染系统日志页面"""
    st.title("📋 系统运行日志")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("数据库连接池", "Active", "正常")
    col2.metric("采集服务延迟", "12ms", "-3ms")
    col3.metric("今日异常记录", "5", "待处理")
    
    st.divider()
    
    log_df = get_system_logs()
    st.markdown("##### 最新采集流水")
    st.dataframe(log_df, use_container_width=True)
    
    render_footer()