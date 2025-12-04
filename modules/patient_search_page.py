import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database.queries import search_patients, query_vital_signs_paginated, get_filter_options
from components.patient_detail import render_patient_detail
from components.common import render_footer

def render_patient_search():
    """渲染患者检索分析页面"""
    st.title("🔍 患者检索分析")
    
    # 状态管理
    if 'search_step' not in st.session_state:
        st.session_state.search_step = 1  # 1: 患者筛选, 2: 体征分析
    if 'selected_patient_id' not in st.session_state:
        st.session_state.selected_patient_id = None
    if 'search_filters' not in st.session_state:
        st.session_state.search_filters = {}

    # 检查是否要显示详情视图
    if st.session_state.get('current_view') == 'detail' and st.session_state.selected_patient_id:
        render_patient_detail_view()
        return

    # 进度指示器
    render_progress_indicator()

    if st.session_state.search_step == 1:
        render_patient_selection_step()
    elif st.session_state.search_step == 2:
        render_vital_signs_analysis_step()

def render_progress_indicator():
    """渲染进度指示器"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        progress_html = """
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;'>
            <div style='display: flex; flex-direction: column; align-items: center;'>
                <div style='width: 30px; height: 30px; border-radius: 50%; background-color: {}; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;'>1</div>
                <span style='margin-top: 5px; font-size: 12px;'>患者筛选</span>
            </div>
            <div style='flex: 1; height: 2px; background-color: {}; margin: 0 10px;'></div>
            <div style='display: flex; flex-direction: column; align-items: center;'>
                <div style='width: 30px; height: 30px; border-radius: 50%; background-color: {}; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;'>2</div>
                <span style='margin-top: 5px; font-size: 12px;'>体征分析</span>
            </div>
        </div>
        """
        
        if st.session_state.search_step == 1:
            st.markdown(progress_html.format("#1f77b4", "#e0e0e0", "#e0e0e0"), unsafe_allow_html=True)
        else:
            st.markdown(progress_html.format("#2ca02c", "#2ca02c", "#1f77b4"), unsafe_allow_html=True)

def render_patient_selection_step():
    """渲染患者选择步骤"""
    st.markdown("### 📋 第一步：患者筛选")
    
    # 筛选条件区域
    with st.container(border=True):
        st.markdown("#### 🔍 筛选条件")
        
        # 获取筛选选项
        filter_opts = get_filter_options()
        
        with st.form("patient_search_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**基本信息**")
                inp_keyword = st.text_input("👤 姓名/住院号", placeholder="输入患者姓名或住院号")
                inp_bed = st.text_input("🛏️ 床号", placeholder="输入床号，如：15")
                sel_location = st.selectbox("🏥 病区/科室", ["全部"] + filter_opts['locations'])
            
            with col2:
                st.markdown("**就诊信息**")
                sel_type = st.selectbox("📋 就诊类型", ["全部"] + filter_opts['types'])
                date_range = st.selectbox("📅 时间范围", [
                    "全部", "今天", "最近3天", "最近7天", "最近30天", "自定义"
                ])
                
                if date_range == "自定义":
                    col_date1, col_date2 = st.columns(2)
                    with col_date1:
                        start_date = st.date_input("开始日期")
                    with col_date2:
                        end_date = st.date_input("结束日期")
            
            col_submit, col_reset, col_space = st.columns([1, 1, 4])
            with col_submit:
                submitted = st.form_submit_button("🔍 开始检索", use_container_width=True, type="primary")
            with col_reset:
                reset_form = st.form_submit_button("🔄 重置", use_container_width=True)
        
        if reset_form:
            # 清空筛选条件
            st.session_state.search_filters = {}
            st.rerun()
        
        if submitted:
            # 保存筛选条件
            st.session_state.search_filters = {
                'name': inp_keyword if inp_keyword else None,
                'pid': inp_keyword if inp_keyword else None,
                'bed_no': inp_bed if inp_bed else None,
                'location': sel_location if sel_location != "全部" else None,
                'p_type': sel_type if sel_type != "全部" else None,
                'date_range': date_range,
                'start_date': start_date if date_range == "自定义" else None,
                'end_date': end_date if date_range == "自定义" else None
            }
    
    # 查询结果显示
    if st.session_state.search_filters:
        render_patient_results()

def render_patient_results():
    """渲染患者查询结果"""
    with st.spinner("正在查询患者数据..."):
        df_patients = search_patients(
            name=st.session_state.search_filters.get('name'),
            pid=st.session_state.search_filters.get('pid'),
            bed_no=st.session_state.search_filters.get('bed_no'),
            location=st.session_state.search_filters.get('location'),
            p_type=st.session_state.search_filters.get('p_type')
        )
    
    if not df_patients.empty:
        st.markdown(f"### 📊 查询结果：共找到 `{len(df_patients)}` 位患者")
        
        # 统计信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总患者数", len(df_patients))
        with col2:
            st.metric("病区分布", df_patients['collection_location'].nunique())
        with col3:
            st.metric("就诊类型", df_patients['patient_type'].nunique())
        with col4:
            # 计算最近24小时有数据更新的患者数
            recent_count = len(df_patients[df_patients['last_time'] > datetime.now() - timedelta(hours=24)])
            st.metric("24小时内活跃", recent_count)
        
        # 直接使用列表视图
        render_list_view(df_patients)
            
    else:
        st.info("🔍 未找到符合条件的患者，请调整筛选条件后重试。")

def render_list_view(df_patients):
    """渲染列表视图"""
    # 显示患者列表
    event = st.dataframe(
        df_patients,
        column_config={
            "patient_id": "患者ID",
            "patient_name": st.column_config.TextColumn("姓名", width="small"),
            "sex": st.column_config.TextColumn("性别", width="small"),
            "age": st.column_config.TextColumn("年龄", width="small"),
            "bed_no": st.column_config.TextColumn("床号", width="small"),
            "collection_location": st.column_config.TextColumn("病区", width="medium"),
            "patient_type": st.column_config.TextColumn("类型", width="small"),
            "last_time": st.column_config.DatetimeColumn("最近采集", format="MM-DD HH:mm", width="medium")
        },
        selection_mode="single-row",
        on_select="rerun",
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    # 处理列表选中并显示操作按钮
    if len(event.selection.rows) > 0:
        selected_row_idx = event.selection.rows[0]
        selected_patient = df_patients.iloc[selected_row_idx]
        
        # 显示选中患者信息和操作按钮
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**已选择**: {selected_patient['patient_name']} ({selected_patient['patient_id']}) - {selected_patient['bed_no']}床")
                st.caption(f"🏥 {selected_patient['collection_location']} | {selected_patient['sex']} | {selected_patient['age']}岁")
            with col2:
                if st.button("📊 体征分析", use_container_width=True, type="primary"):
                    st.session_state.selected_patient_id = selected_patient['patient_id']
                    st.session_state.search_step = 2
                    st.rerun()
            with col3:
                if st.button("📋 详细信息", use_container_width=True):
                    st.session_state.selected_patient_id = selected_patient['patient_id']
                    st.session_state.current_view = 'detail'
                    st.rerun()



def render_vital_signs_analysis_step():
    """渲染体征分析步骤"""
    if not st.session_state.selected_patient_id:
        st.error("未选择患者，请返回第一步选择患者")
        if st.button("⬅️ 返回患者选择"):
            st.session_state.search_step = 1
            st.session_state.selected_patient_id = None
            st.rerun()
        return
    
    # 返回按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ 返回患者列表", use_container_width=True):
            st.session_state.search_step = 1
            st.session_state.selected_patient_id = None
            st.rerun()
    
    # 获取患者基本信息
    patient_info = get_patient_basic_info(st.session_state.selected_patient_id)
    if not patient_info.empty:
        patient = patient_info.iloc[0]
        with col2:
            st.markdown(f"### 👤 当前患者：{patient['patient_name']} ({st.session_state.selected_patient_id})")
            st.caption(f"🛏️ {patient['bed_no']}床 | 🏥 {patient['collection_location']} | {patient['sex']} | {patient['age']}岁")
    
    with col3:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # 体征数据筛选
    render_vital_signs_filters()
    
    # 体征数据分析
    render_vital_signs_analysis()

def render_vital_signs_filters():
    """渲染体征数据筛选"""
    st.markdown("### 📋 第二步：体征数据筛选")
    
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=7))
        with col2:
            end_date = st.date_input("结束日期", value=datetime.now())
        with col3:
            vital_types = st.multiselect(
                "体征类型",
                ["体温", "脉搏", "呼吸", "血压", "血氧饱和度", "心输出量"],
                default=["体温", "脉搏", "呼吸", "血压", "血氧饱和度"]
            )
        with col4:
            abnormal_only = st.checkbox("仅显示异常数据", value=False)
        
        # 应用筛选按钮
        if st.button("🔄 应用筛选", use_container_width=True):
            st.session_state.vital_filters = {
                'start_date': start_date,
                'end_date': end_date,
                'vital_types': vital_types,
                'abnormal_only': abnormal_only
            }
            st.rerun()

def render_vital_signs_analysis():
    """渲染体征数据分析"""
    # 获取筛选条件
    filters = st.session_state.get('vital_filters', {
        'start_date': datetime.now() - timedelta(days=7),
        'end_date': datetime.now(),
        'vital_types': ["体温", "脉搏", "呼吸", "血压", "血氧饱和度"],
        'abnormal_only': False
    })
    
    with st.spinner("正在查询体征数据..."):
        df_vitals = query_vital_signs_paginated(
            st.session_state.selected_patient_id,
            datetime.combine(filters['start_date'], datetime.min.time()),
            datetime.combine(filters['end_date'], datetime.max.time())
        )
    
    if not df_vitals.empty:
        # 数据预处理
        df_vitals['standard_field_value'] = pd.to_numeric(df_vitals['standard_field_value'], errors='coerce')
        
        # 筛选体征类型
        if filters['vital_types']:
            df_vitals = df_vitals[df_vitals['description'].isin(filters['vital_types'])]
        
        # 筛选异常数据
        if filters['abnormal_only']:
            df_vitals = filter_abnormal_data(df_vitals)
        
        st.markdown(f"### 📊 数据分析结果：共 `{len(df_vitals)}` 条体征记录")
        
        # 分析标签页
        tab1, tab2, tab3, tab4 = st.tabs(["📈 趋势图", "📊 统计分析", "⚠️ 异常检测", "📋 数据详情"])
        
        with tab1:
            render_trend_charts(df_vitals)
        
        with tab2:
            render_statistical_analysis(df_vitals)
        
        with tab3:
            render_abnormal_detection(df_vitals)
        
        with tab4:
            render_data_details(df_vitals)
            
    else:
        st.warning("⚠️ 该时间段内未找到体征数据，请调整筛选条件。")

def filter_abnormal_data(df):
    """筛选异常数据"""
    abnormal_data = []
    for _, row in df.iterrows():
        normal_range = get_normal_range(row['description'])
        if normal_range:
            value = row['standard_field_value']
            if pd.notna(value) and (value < normal_range['min'] or value > normal_range['max']):
                abnormal_data.append(True)
            else:
                abnormal_data.append(False)
        else:
            abnormal_data.append(False)
    
    return df[abnormal_data]

def render_trend_charts(df_vitals):
    """渲染趋势图表"""
    if df_vitals.empty:
        st.info("暂无数据显示")
        return
    
    vital_signs = df_vitals['description'].unique()
    
    for vital in vital_signs:
        vital_data = df_vitals[df_vitals['description'] == vital].sort_values('collection_time')
        
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
                yaxis_title=f"数值 ({vital_data['unit'].iloc[0] if 'unit' in vital_data.columns else ''})",
                height=300,
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

def render_statistical_analysis(df_vitals):
    """渲染统计分析"""
    if df_vitals.empty:
        st.info("暂无数据统计")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 箱线图
        fig_box = px.box(
            df_vitals, 
            x='description', 
            y='standard_field_value', 
            color='description',
            title="各项体征数值分布",
            labels={'description': '体征项目', 'standard_field_value': '数值'}
        )
        fig_box.update_layout(height=400, template="plotly_white")
        st.plotly_chart(fig_box, use_container_width=True)
    
    with col2:
        # 统计摘要
        stats_summary = []
        for vital in df_vitals['description'].unique():
            vital_data = df_vitals[df_vitals['description'] == vital]['standard_field_value']
            if not vital_data.empty:
                normal_range = get_normal_range(vital)
                abnormal_count = 0
                if normal_range:
                    abnormal_count = len(vital_data[
                        (vital_data < normal_range['min']) | (vital_data > normal_range['max'])
                    ])
                
                stats_summary.append({
                    '体征项目': vital,
                    '测量次数': len(vital_data),
                    '平均值': f"{vital_data.mean():.2f}",
                    '标准差': f"{vital_data.std():.2f}",
                    '最小值': f"{vital_data.min():.2f}",
                    '最大值': f"{vital_data.max():.2f}",
                    '异常次数': abnormal_count
                })
        
        if stats_summary:
            st.dataframe(pd.DataFrame(stats_summary), use_container_width=True, hide_index=True)

def render_abnormal_detection(df_vitals):
    """渲染异常检测"""
    abnormal_data = []
    for vital in df_vitals['description'].unique():
        vital_data = df_vitals[df_vitals['description'] == vital]
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
        st.warning(f"⚠️ 检测到 `{len(abnormal_data)}` 个异常数据点")
        
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
        
        # 异常分布图
        vital_counts = pd.DataFrame(abnormal_data)['description'].value_counts()
        fig_abnormal = px.bar(
            x=vital_counts.index,
            y=vital_counts.values,
            title="异常数据分布",
            labels={'x': '体征项目', 'y': '异常次数'}
        )
        fig_abnormal.update_layout(height=300, template="plotly_white")
        st.plotly_chart(fig_abnormal, use_container_width=True)
    else:
        st.success("✅ 未检测到异常数据，所有体征指标均在正常范围内。")

def render_data_details(df_vitals):
    """渲染数据详情"""
    if df_vitals.empty:
        st.info("暂无详细数据")
        return
    
    # 数据筛选
    col1, col2 = st.columns(2)
    with col1:
        selected_vital = st.selectbox("选择体征项目", df_vitals['description'].unique())
    with col2:
        sort_by = st.selectbox("排序方式", ["时间升序", "时间降序", "数值升序", "数值降序"])
    
    # 筛选和排序数据
    filtered_df = df_vitals[df_vitals['description'] == selected_vital].copy()
    
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
        filtered_df[['collection_time', 'standard_field_value', 'description']],
        column_config={
            'collection_time': '采集时间',
            'standard_field_value': '数值',
            'description': '体征项目'
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
        '血氧饱和度': {'min': 95, 'max': 100},
        '心输出量': {'min': 4.0, 'max': 8.0}
    }
    return ranges.get(vital_sign)

def render_patient_detail_view():
    """渲染患者详情视图"""
    # 返回按钮
    if st.button("⬅️ 返回患者列表"):
        st.session_state.current_view = None
        st.session_state.search_step = 1
        st.rerun()
    
    # 渲染患者详情
    from components.patient_detail import render_patient_detail
    render_patient_detail(st.session_state.selected_patient_id)

def get_patient_basic_info(patient_id):
    """获取患者基本信息"""
    from database.queries import get_patient_basic_info
    return get_patient_basic_info(patient_id)