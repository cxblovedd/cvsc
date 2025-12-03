import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database.queries import get_patient_basic_info, query_vital_signs_paginated
from utils.helpers import get_status_color, highlight_status_row, calculate_time_range

def render_patient_detail(patient_id):
    """渲染患者详情页组件"""
    # 获取患者基本信息
    patient_info_df = get_patient_basic_info(patient_id)
    
    if patient_info_df.empty:
        st.error(f"未找到 ID 为 {patient_id} 的患者信息")
        return

    patient_info = patient_info_df.iloc[0]
    
    # 顶部：患者信息卡片
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(f"**👤 姓名**: {patient_info['patient_name'] or '--'}")
        c2.markdown(f"**🆔 ID**: {patient_id}")
        c3.markdown(f"**⚧️ 性别/年龄**: {patient_info['sex']}/{patient_info['age']}")
        c4.markdown(f"**🏥 病区**: {patient_info['collection_location'] or '--'}")
        c5.markdown(f"**🛏️ 床号**: {patient_info['bed_no'] or '--'}")

    # 时间筛选栏
    c_filter1, c_filter2 = st.columns([3, 1])
    with c_filter1:
        time_range = st.radio("时间范围", ["最近12小时", "最近24小时", "最近3天", "最近7天"], horizontal=True, label_visibility="collapsed")
    
    # 计算时间
    start_t = calculate_time_range(time_range)
    now = datetime.now()
    
    # 查询数据
    with st.spinner("正在分析体征数据..."):
        df_vital = query_vital_signs_paginated(patient_id, start_t, now)
    
    if not df_vital.empty:
        # 数据清洗与预处理
        df_vital['standard_field_value'] = pd.to_numeric(df_vital['standard_field_value'], errors='coerce')
        df_vital = df_vital.dropna(subset=['standard_field_value'])
        df_vital['display_name'] = df_vital.apply(lambda x: x['description'] if x['description'] else x['field_name'], axis=1)
        
        # 定义状态判断函数
        df_vital['status_label'] = df_vital.apply(
            lambda row: get_status_color(row['standard_field_value'], row['normal_range_low'], row['normal_range_high']), 
            axis=1
        )

        # Tab 分页展示
        tab_chart, tab_data = st.tabs(["📈 趋势分析", "📋 详细记录"])
        
        with tab_chart:
            col_sel, col_chart = st.columns([1, 4])
            with col_sel:
                vital_options = df_vital['display_name'].unique()
                selected_vital = st.radio("选择指标", vital_options)
            
            with col_chart:
                chart_data = df_vital[df_vital['display_name'] == selected_vital].copy()
                if not chart_data.empty:
                    fig = px.line(chart_data, x='collection_time', y='standard_field_value', markers=True, 
                                  title=f"{selected_vital} 趋势变化", template="plotly_white")
                    
                    # 添加阈值线
                    limit_row = chart_data.iloc[0]
                    if pd.notnull(limit_row['normal_range_high']):
                        fig.add_hline(y=limit_row['normal_range_high'], line_dash="dash", line_color="red", annotation_text="上限")
                    if pd.notnull(limit_row['normal_range_low']):
                        fig.add_hline(y=limit_row['normal_range_low'], line_dash="dash", line_color="orange", annotation_text="下限")
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("无数据")

        with tab_data:
            display_cols = ['collection_time', 'display_name', 'standard_field_value', 'unit', 'status_label', 'normal_range_low', 'normal_range_high']
            st.dataframe(
                df_vital[display_cols].style.apply(highlight_status_row, axis=1),
                column_config={
                    "collection_time": st.column_config.DatetimeColumn("采集时间", format="MM-DD HH:mm"),
                    "display_name": "体征项目",
                    "standard_field_value": "数值",
                    "unit": "单位",
                    "status_label": "状态评价",
                    "normal_range_low": "参考下限",
                    "normal_range_high": "参考上限"
                },
                use_container_width=True,
                height=500
            )
    else:
        st.warning("📭 该时间段内无体征数据记录")