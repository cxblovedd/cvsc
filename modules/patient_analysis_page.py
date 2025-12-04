import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database.queries import search_patients, query_vital_signs_paginated
from components.common import render_footer

def render_patient_analysis():
    """渲染患者数据分析页面"""
    st.title("📈 历史数据分析")
    
    # 患者选择区域
    with st.container():
        st.markdown("### 🔍 患者选择")
        col1, col2 = st.columns([2, 1])
        with col1:
            search_term = st.text_input("输入患者姓名或ID搜索", placeholder="请输入姓名或住院号")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # 占位符
            quick_search = st.selectbox("快速选择", ["最近监护患者", "今日就诊", "重症患者"], index=0)
    
    if search_term or quick_search != "最近监护患者":
        if search_term:
            patients = search_patients(name=search_term, pid=search_term)
        else:
            patients = get_quick_search_patients(quick_search)
            
        if not patients.empty:
            # 患者信息展示
            selected_pid = st.selectbox(
                "选择患者进行分析", 
                patients['patient_id'].tolist(),
                format_func=lambda x: f"{x} - {patients[patients['patient_id']==x]['patient_name'].values[0]} ({patients[patients['patient_id']==x]['bed_no'].values[0]}床)"
            )
            
            if selected_pid:
                patient_info = patients[patients['patient_id']==selected_pid].iloc[0]
                
                # 患者基本信息卡片
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("患者姓名", patient_info['patient_name'])
                    with col2:
                        st.metric("性别年龄", f"{patient_info['sex']} / {patient_info['age']}")
                    with col3:
                        st.metric("床号", patient_info['bed_no'])
                    with col4:
                        st.metric("病区", patient_info['collection_location'])
                
                st.divider()
                
                # 分析选项卡
                tab1, tab2, tab3, tab4 = st.tabs(["📊 趋势分析", "📈 统计分布", "⚠️ 异常检测", "📋 详细数据"])
                
                # 日期范围选择（在所有标签页上方）
                with st.container():
                    d_col1, d_col2, d_col3 = st.columns([1, 1, 2])
                    with d_col1:
                        start_d = st.date_input("开始日期", value=datetime.now()-timedelta(days=7))
                    with d_col2:
                        end_d = st.date_input("结束日期", value=datetime.now())
                    with d_col3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        vital_types = st.multiselect(
                            "体征类型筛选",
                            ["体温", "脉搏", "呼吸", "血压", "血氧饱和度"],
                            default=["体温", "脉搏", "呼吸", "血压", "血氧饱和度"]
                        )
                
                # 获取数据
                df_analysis = query_vital_signs_paginated(
                    selected_pid, 
                    datetime.combine(start_d, datetime.min.time()),
                    datetime.combine(end_d, datetime.max.time())
                )
                
                if not df_analysis.empty:
                    df_analysis['standard_field_value'] = pd.to_numeric(df_analysis['standard_field_value'], errors='coerce')
                    
                    with tab1:
                        render_trend_analysis(df_analysis, vital_types)
                    
                    with tab2:
                        render_statistical_analysis(df_analysis, vital_types)
                    
                    with tab3:
                        render_abnormal_detection(df_analysis, vital_types)
                    
                    with tab4:
                        render_detailed_data(df_analysis)
                        
                else:
                    st.warning("该时间段无数据，请调整时间范围或选择其他患者。")
        else:
            st.info("未找到符合条件的患者，请检查搜索条件。")
    
    render_footer()

def render_trend_analysis(df, vital_types):
    """渲染趋势分析"""
    st.subheader("📈 体征趋势变化")
    
    # 按体征类型分组绘制趋势图
    vital_signs = df['description'].unique()
    
    for vital in vital_signs:
        if vital in vital_types:
            vital_data = df[df['description'] == vital].sort_values('collection_time')
            
            if not vital_data.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=vital_data['collection_time'],
                    y=vital_data['standard_field_value'],
                    mode='lines+markers',
                    name=vital,
                    line=dict(width=2),
                    marker=dict(size=4)
                ))
                
                # 添加正常范围参考线
                normal_range = get_normal_range(vital)
                if normal_range:
                    fig.add_hline(y=normal_range['min'], line_dash="dash", line_color="green", opacity=0.5)
                    fig.add_hline(y=normal_range['max'], line_dash="dash", line_color="green", opacity=0.5)
                    fig.add_annotation(
                        text=f"正常范围: {normal_range['min']}-{normal_range['max']}",
                        xref="paper", yref="y", x=0.02, y=normal_range['max'],
                        showarrow=False, font=dict(size=10, color="green")
                    )
                
                fig.update_layout(
                    title=f"{vital}趋势图",
                    xaxis_title="时间",
                    yaxis_title="数值",
                    height=300,
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)

def render_statistical_analysis(df, vital_types):
    """渲染统计分析"""
    st.subheader("📊 数据分布统计")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 箱线图分析分布
        filtered_df = df[df['description'].isin(vital_types)]
        if not filtered_df.empty:
            fig_box = px.box(
                filtered_df, 
                x='description', 
                y='standard_field_value', 
                color='description',
                title="各项体征数值分布范围",
                labels={'description': '体征项', 'standard_field_value': '数值'}
            )
            fig_box.update_layout(height=400, template="plotly_white")
            st.plotly_chart(fig_box, use_container_width=True)
    
    with col2:
        # 统计摘要表格
        stats_summary = []
        for vital in vital_types:
            vital_data = df[df['description'] == vital]['standard_field_value']
            if not vital_data.empty:
                stats_summary.append({
                    '体征项目': vital,
                    '平均值': f"{vital_data.mean():.2f}",
                    '标准差': f"{vital_data.std():.2f}",
                    '最小值': f"{vital_data.min():.2f}",
                    '最大值': f"{vital_data.max():.2f}",
                    '测量次数': len(vital_data)
                })
        
        if stats_summary:
            st.dataframe(pd.DataFrame(stats_summary), use_container_width=True, hide_index=True)

def render_abnormal_detection(df, vital_types):
    """渲染异常检测"""
    st.subheader("⚠️ 异常检测分析")
    
    abnormal_data = []
    for vital in vital_types:
        vital_data = df[df['description'] == vital]
        if not vital_data.empty:
            normal_range = get_normal_range(vital)
            if normal_range:
                abnormal = vital_data[
                    (vital_data['standard_field_value'] < normal_range['min']) |
                    (vital_data['standard_field_value'] > normal_range['max'])
                ]
                if not abnormal.empty:
                    abnormal_data.extend(abnormal.to_dict('records'))
    
    if abnormal_data:
        st.warning(f"检测到 {len(abnormal_data)} 个异常数据点")
        
        # 异常数据表格
        abnormal_df = pd.DataFrame(abnormal_data)
        st.dataframe(
            abnormal_df[['collection_time', 'description', 'standard_field_value']],
            column_config={
                'collection_time': '异常时间',
                'description': '体征项目',
                'standard_field_value': '异常数值'
            },
            use_container_width=True,
            hide_index=True
        )
        
        # 异常趋势图
        fig = px.scatter(
            pd.DataFrame(abnormal_data),
            x='collection_time',
            y='standard_field_value',
            color='description',
            title="异常数据点分布",
            labels={'collection_time': '时间', 'standard_field_value': '数值', 'description': '体征项目'}
        )
        fig.update_layout(height=400, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("✅ 未检测到异常数据，所有体征指标均在正常范围内。")

def render_detailed_data(df):
    """渲染详细数据"""
    st.subheader("📋 原始数据详情")
    
    # 数据筛选
    col1, col2 = st.columns(2)
    with col1:
        selected_vital = st.selectbox("选择体征项目", df['description'].unique())
    with col2:
        sort_by = st.selectbox("排序方式", ["时间升序", "时间降序", "数值升序", "数值降序"])
    
    # 筛选和排序数据
    filtered_df = df[df['description'] == selected_vital].copy()
    
    if sort_by == "时间升序":
        filtered_df = filtered_df.sort_values('collection_time')
    elif sort_by == "时间降序":
        filtered_df = filtered_df.sort_values('collection_time', ascending=False)
    elif sort_by == "数值升序":
        filtered_df = filtered_df.sort_values('standard_field_value')
    elif sort_by == "数值降序":
        filtered_df = filtered_df.sort_values('standard_field_value', ascending=False)
    
    # 数据导出
    csv_data = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 导出CSV数据",
        data=csv_data,
        file_name=f"vital_signs_{selected_vital}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime='text/csv'
    )
    
    # 数据表格
    st.dataframe(
        filtered_df[['collection_time', 'standard_field_value', 'device_model_name']],
        column_config={
            'collection_time': '采集时间',
            'standard_field_value': '数值',
            'device_model_name': '设备型号'
        },
        use_container_width=True,
        hide_index=True
    )

def get_normal_range(vital_sign):
    """获取体征正常范围"""
    ranges = {
        '体温': {'min': 36.0, 'max': 37.5},
        '脉搏': {'min': 60, 'max': 100},
        '呼吸': {'min': 12, 'max': 20},
        '血压': {'min': 90, 'max': 140},
        '血氧饱和度': {'min': 95, 'max': 100}
    }
    return ranges.get(vital_sign)

@st.cache_data(ttl=300)
def get_quick_search_patients(search_type):
    """快速搜索患者"""
    # 这里应该调用实际的数据库查询
    # 暂时返回空DataFrame
    return pd.DataFrame()