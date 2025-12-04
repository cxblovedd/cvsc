import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database.queries import search_patients, get_filter_options, get_dashboard_stats
from components.patient_detail import render_patient_detail
from components.common import render_footer

def render_dashboard():
    """渲染实时监控看板页面"""
    st.title("📊 全院体征实时监控")
    
    # 实时监控概览
    render_realtime_overview()
    
    st.divider()
    
    # 病区监控状态
    render_location_monitoring()
    
    st.divider()
    
    # 实时告警信息
    render_realtime_alerts()
    
    st.divider()
    
    # 设备状态监控
    render_device_monitoring()
    
    # 自动刷新
    render_auto_refresh()

def render_realtime_overview():
    """渲染实时监控概览"""
    st.markdown("### 🏥 实时监控概览")
    
    stats = get_dashboard_stats()
    
    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="🖥️ 在线设备",
            value=stats.get('online_devices', 0),
            delta=f"{stats.get('online_rate', 0)}% 在线率",
            delta_color="normal"
        )
    with col2:
        st.metric(
            label="👥 监护患者", 
            value=stats.get('monitored_patients', 0),
            delta=f"+{stats.get('patient_change', 0)} 较昨日",
            delta_color="normal"
        )
    with col3:
        st.metric(
            label="📊 实时采集",
            value=f"{stats.get('collection_rate', 0)}/分",
            delta=f"{stats.get('today_collections', 0)} 今日累计",
            delta_color="normal"
        )
    with col4:
        alert_delta = stats.get('new_alerts', 0)
        st.metric(
            label="⚠️ 活跃告警",
            value=stats.get('active_alerts', 0),
            delta=f"+{alert_delta} 新增" if alert_delta > 0 else f"-{abs(alert_delta)} 已处理",
            delta_color="inverse" if alert_delta > 0 else "normal"
        )
    
    # 实时趋势图
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("#### 📈 24小时采集趋势")
        trend_data = get_collection_trend()
        if not trend_data.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trend_data['time'], 
                y=trend_data['count'],
                mode='lines+markers',
                name='采集次数',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=6),
                fill='tozeroy'
            ))
            fig.update_layout(
                title="数据采集频率趋势",
                xaxis_title="时间",
                yaxis_title="采集次数/小时",
                height=300,
                showlegend=False,
                template="plotly_white",
                margin=dict(l=0, r=0, t=30, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 🎯 系统健康度")
        health_score = calculate_system_health(stats)
        
        # 健康度仪表盘
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = health_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "健康度评分"},
            delta = {'reference': 90},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#1f77b4"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig.update_layout(height=300, template="plotly_white", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

def render_location_monitoring():
    """渲染病区监控状态"""
    st.markdown("### 🏥 病区监护状态")
    
    location_stats = get_location_stats()
    if not location_stats.empty:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 病区状态分布图
            fig = go.Figure()
            
            locations = location_stats['location'].tolist()
            normal_counts = location_stats['normal_count'].tolist()
            warning_counts = location_stats['warning_count'].tolist()
            critical_counts = location_stats['critical_count'].tolist()
            
            fig.add_trace(go.Bar(name='正常', x=locations, y=normal_counts, marker_color='#2E8B57'))
            fig.add_trace(go.Bar(name='警告', x=locations, y=warning_counts, marker_color='#FFD700'))
            fig.add_trace(go.Bar(name='危急', x=locations, y=critical_counts, marker_color='#DC143C'))
            
            fig.update_layout(
                title="各病区患者状态分布",
                xaxis_title="病区",
                yaxis_title="患者数",
                barmode='stack',
                height=350,
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 📊 状态统计")
            
            total_patients = location_stats[['normal_count', 'warning_count', 'critical_count']].sum().sum()
            total_normal = location_stats['normal_count'].sum()
            total_warning = location_stats['warning_count'].sum()
            total_critical = location_stats['critical_count'].sum()
            
            st.metric("总监护数", total_patients)
            st.metric("正常比例", f"{(total_normal/total_patients*100):.1f}%" if total_patients > 0 else "0%")
            st.metric("警告数量", total_warning, delta=f"{(total_warning/total_patients*100):.1f}%" if total_patients > 0 else "0%")
            st.metric("危急数量", total_critical, delta=f"{(total_critical/total_patients*100):.1f}%" if total_patients > 0 else "0%", delta_color="inverse")
            
            st.markdown("**状态说明**")
            st.markdown("🟢 正常：体征稳定")
            st.markdown("🟡 警告：需关注")
            st.markdown("🔴 危急：需立即处理")
    else:
        st.info("暂无病区数据")

def render_realtime_alerts():
    """渲染实时告警信息"""
    st.markdown("### ⚠️ 实时告警监控")
    
    alerts = get_active_alerts()
    
    if not alerts.empty:
        # 告警统计
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            critical_count = len(alerts[alerts['severity'] == '危急'])
            st.metric("🔴 危急", critical_count, delta_color="inverse")
        with col2:
            warning_count = len(alerts[alerts['severity'] == '警告'])
            st.metric("🟡 警告", warning_count)
        with col3:
            info_count = len(alerts[alerts['severity'] == '提示'])
            st.metric("🔵 提示", info_count)
        with col4:
            st.metric("📊 总计", len(alerts))
        
        # 告警列表
        st.markdown("#### 🚨 最新告警")
        
        # 按严重程度排序
        alerts_sorted = alerts.sort_values(['severity', 'timestamp'], ascending=[False, False])
        
        for _, alert in alerts_sorted.head(10).iterrows():
            severity_color = {
                '危急': 'red',
                '警告': 'orange', 
                '提示': 'blue'
            }.get(alert['severity'], 'gray')
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    st.markdown(f"🔴<br>{alert['severity']}", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"**{alert['patient_name']}** ({alert['bed_no']}床)")
                    st.caption(f"{alert['message']} - {alert['timestamp'].strftime('%H:%M:%S')}")
                with col3:
                    if st.button("处理", key=f"handle_{alert['id']}", use_container_width=True):
                        st.session_state.selected_patient_id = alert['patient_id']
                        st.info(f"已跳转到患者 {alert['patient_name']} 的详细信息")
    else:
        st.success("✅ 当前无活跃告警，系统运行正常")

def render_device_monitoring():
    """渲染设备状态监控"""
    st.markdown("### 🖥️ 设备状态监控")
    
    device_stats = get_device_monitoring_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        # 设备状态饼图
        if not device_stats.empty:
            fig = px.pie(
                values=device_stats['count'].values,
                names=device_stats['status'].values,
                title="设备状态分布",
                color_discrete_map={
                    '在线': '#2E8B57',
                    '离线': '#DC143C',
                    '维护': '#FFD700'
                }
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # 设备详细信息
        st.markdown("#### 📋 设备清单")
        device_list = get_device_list()
        if not device_list.empty:
            # 只显示前10台设备
            display_devices = device_list.head(10)
            
            for _, device in display_devices.iterrows():
                status_icon = "🟢" if device['monitor_status'] == '在线' else "🔴"
                use_icon = "🔄" if device['use_status'] == '使用中' else "⏸️"
                
                st.markdown(f"{status_icon} {use_icon} **{device['monitor_name']}**")
                st.caption(f"编号: {device['monitor_code']} | 状态: {device['monitor_status']}")
    
    with col3:
        # 设备性能指标
        st.markdown("#### ⚡ 性能指标")
        perf_metrics = get_device_performance_metrics()
        
        st.metric("平均响应时间", f"{perf_metrics.get('avg_response_time', 0)}ms")
        st.metric("数据成功率", f"{perf_metrics.get('success_rate', 0)}%")
        st.metric("故障率", f"{perf_metrics.get('failure_rate', 0)}%", delta_color="inverse")
        st.metric("维护计划", f"{perf_metrics.get('scheduled_maintenance', 0)}台")

def render_auto_refresh():
    """渲染自动刷新控制"""
    st.markdown("### 🔄 自动刷新")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        refresh_interval = st.selectbox(
            "刷新间隔",
            [30, 60, 120, 300],
            format_func=lambda x: f"{x}秒",
            index=1
        )
    
    with col2:
        st.markdown("**最后更新时间**")
        last_update = st.session_state.get('last_update', datetime.now())
        st.caption(last_update.strftime("%Y-%m-%d %H:%M:%S"))
    
    with col3:
        if st.button("🔄 立即刷新", use_container_width=True):
            st.session_state.last_update = datetime.now()
            st.rerun()
    
    # 自动刷新逻辑
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
    
    time_since_update = (datetime.now() - st.session_state.last_update).total_seconds()
    if time_since_update > refresh_interval:
        st.session_state.last_update = datetime.now()
        st.rerun()

def calculate_system_health(stats):
    """计算系统健康度评分"""
    try:
        # 基于多个指标计算健康度
        online_rate = stats.get('online_rate', 0) / 100
        collection_rate = min(stats.get('collection_rate', 0) / 10, 1)  # 假设10次/分为满分
        alert_ratio = max(0, 1 - stats.get('active_alerts', 0) / 50)  # 假设50个告警为0分
        
        health_score = (online_rate * 0.4 + collection_rate * 0.3 + alert_ratio * 0.3) * 100
        return round(health_score, 1)
    except:
        return 85.0  # 默认健康度
        
        if not df_patients.empty:
            st.markdown(f"**查询结果**: 共找到 `{len(df_patients)}` 位患者")
            
            view_mode = st.radio("视图模式", ["📇 卡片视图", "📄 列表视图"], horizontal=True, label_visibility="collapsed")
            
            if view_mode == "📄 列表视图":
                # 列表视图
                event = st.dataframe(
                    df_patients,
                    column_config={
                        "patient_id": "ID",
                        "patient_name": "姓名",
                        "sex": "性别",
                        "age": "年龄",
                        "bed_no": "床号",
                        "collection_location": "病区",
                        "patient_type": "类型",
                        "last_time": st.column_config.DatetimeColumn("最近采集", format="MM-DD HH:mm")
                    },
                    selection_mode="single-row",
                    on_select="rerun",
                    use_container_width=True,
                    height=400,
                    hide_index=True
                )
                
                # 处理列表选中
                if len(event.selection.rows) > 0:
                    selected_row_idx = event.selection.rows[0]
                    pid = df_patients.iloc[selected_row_idx]['patient_id']
                    st.session_state.selected_patient_id = pid
                    st.session_state.current_view = 'detail'
                    st.rerun()
            else:
                # 卡片视图 (Grid Layout)
                cols = st.columns(5)
                for idx, row in df_patients.iterrows():
                    with cols[idx % 5]:
                        with st.container(border=True):
                            st.markdown(f"#### {row['bed_no'] or '待定'}")
                            st.markdown(f"**{row['patient_name']}**")
                            st.caption(f"{row['sex']} | {row['age']}")
                            
                            # 模拟状态指示点（根据最近采集时间）
                            from datetime import datetime
                            time_diff = (datetime.now() - row['last_time']).total_seconds() / 3600
                            status_color = "🟢" if time_diff < 1 else ("🟡" if time_diff < 4 else "⚪")
                            st.caption(f"{status_color} {row['last_time'].strftime('%H:%M')}")
                            
                            # 确保按钮键是唯一的，即使patient_id重复
                            btn_key = f"btn_{row['patient_id']}_{idx}"
                            if st.button("查看", key=btn_key, use_container_width=True):
                                st.session_state.selected_patient_id = row['patient_id']
                                st.session_state.current_view = 'detail'
                                st.rerun()
        else:
            st.info("未找到符合条件的患者，请调整筛选条件。")
    
    render_footer()

@st.cache_data(ttl=300)  # 缓存5分钟
def get_dashboard_stats():
    """获取仪表板统计数据"""
    try:
        # 这里应该调用实际的数据库查询
        # 暂时返回模拟数据
        return {
            'online_devices': 45,
            'new_devices_today': 3,
            'monitored_patients': 128,
            'patient_change': 5.2,
            'today_collections': 3847,
            'collection_rate': 2.7,
            'abnormal_alerts': 12,
            'resolved_alerts': 8
        }
    except Exception as e:
        st.error(f"获取统计数据失败: {e}")
        return {}

@st.cache_data(ttl=60)  # 缓存1分钟
def get_collection_trend():
    """获取采集趋势数据"""
    try:
        # 生成过去24小时的模拟数据
        times = pd.date_range(end=datetime.now(), periods=24, freq='H')
        counts = [50 + i*2 + (i%3)*10 for i in range(24)]  # 模拟数据
        return pd.DataFrame({'time': times, 'count': counts})
    except Exception as e:
        st.error(f"获取趋势数据失败: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)  # 缓存5分钟
def get_location_stats():
    """获取病区统计数据"""
    try:
        # 模拟病区数据
        data = {
            'location': ['ICU', '内科', '外科', '儿科', '妇产科'],
            'normal_count': [15, 28, 22, 18, 12],
            'warning_count': [3, 5, 4, 2, 1],
            'critical_count': [2, 1, 2, 1, 0]
        }
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"获取病区统计失败: {e}")
        return pd.DataFrame()