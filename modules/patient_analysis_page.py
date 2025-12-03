import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from database.queries import search_patients, query_vital_signs_paginated
from components.common import render_footer

def render_patient_analysis():
    """渲染患者数据分析页面"""
    st.title("📈 历史数据分析")
    
    st.markdown("### 🔍 患者选择")
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("输入患者姓名或ID搜索")
    
    if search_term:
        patients = search_patients(name=search_term, pid=search_term)
        if not patients.empty:
            selected_pid = st.selectbox(
                "选择患者", 
                patients['patient_id'].tolist(),
                format_func=lambda x: f"{x} - {patients[patients['patient_id']==x]['patient_name'].values[0]}"
            )
            
            if selected_pid:
                st.divider()
                st.subheader("📊 多维度对比分析")
                
                # 日期范围
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    start_d = st.date_input("开始日期", value=datetime.now()-timedelta(days=7))
                with d_col2:
                    end_d = st.date_input("结束日期", value=datetime.now())
                
                df_analysis = query_vital_signs_paginated(
                    selected_pid, 
                    datetime.combine(start_d, datetime.min.time()),
                    datetime.combine(end_d, datetime.max.time())
                )
                
                if not df_analysis.empty:
                    df_analysis['standard_field_value'] = pd.to_numeric(df_analysis['standard_field_value'], errors='coerce')
                    
                    # 箱线图分析分布
                    fig_box = px.box(
                        df_analysis, 
                        x='description', 
                        y='standard_field_value', 
                        color='description',
                        title="各项体征数值分布范围",
                        labels={'description': '体征项', 'standard_field_value': '数值'}
                    )
                    st.plotly_chart(fig_box, use_container_width=True)
                else:
                    st.warning("该时间段无数据")
        else:
            st.info("未找到患者")
    
    render_footer()