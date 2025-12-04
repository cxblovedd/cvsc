import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database.queries import get_system_logs, get_system_stats, get_error_logs, get_performance_metrics
from components.common import render_footer

def render_system_logs():
    """渲染系统日志页面"""
    st.title("📋 系统运行日志")
    
    # 系统状态概览
    render_system_status()
    
    st.divider()
    
    # 主要功能标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 系统概览", "📝 运行日志", "⚠️ 异常监控", "📈 性能分析", "🔍 日志查询"])
    
    with tab1:
        render_system_overview()
    
    with tab2:
        render_runtime_logs()
    
    with tab3:
        render_error_monitoring()
    
    with tab4:
        render_performance_analysis()
    
    with tab5:
        render_log_search()
    
    render_footer()

def render_system_status():
    """渲染系统状态概览"""
    stats = get_system_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_color = "🟢" if stats.get('db_status') == '正常' else "🔴"
        st.metric(
            label=f"{status_color} 数据库连接",
            value=stats.get('db_status', '未知'),
            delta=f"连接池: {stats.get('db_pool_size', 0)}/{stats.get('db_pool_max', 0)}"
        )
    with col2:
        st.metric(
            label="🔄 采集服务",
            value=f"{stats.get('collection_delay', 0)}ms",
            delta=f"{stats.get('delay_change', 0)}ms 较上小时"
        )
    with col3:
        alert_color = "🟡" if stats.get('error_count', 0) > 0 else "🟢"
        st.metric(
            label=f"{alert_color} 今日异常",
            value=stats.get('error_count', 0),
            delta=f"-{stats.get('resolved_errors', 0)} 已处理"
        )
    with col4:
        st.metric(
            label="📊 数据吞吐",
            value=f"{stats.get('data_throughput', 0)}/min",
            delta=f"{stats.get('throughput_change', 0)}% 较昨日"
        )

def render_system_overview():
    """渲染系统概览"""
    st.subheader("📊 系统整体状态")
    
    # 服务状态监控
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 服务状态")
        services = get_service_status()
        if not services.empty:
            fig_services = go.Figure()
            
            # 创建状态指示器
            for i, service in services.iterrows():
                status_value = 1 if service['status'] == '运行中' else 0
                color = '#2E8B57' if service['status'] == '运行中' else '#DC143C'
                
                fig_services.add_trace(go.Indicator(
                    mode="number+gauge+delta",
                    value=status_value,
                    domain={'x': [0, 1], 'y': [i/services.shape[0], (i+1)/services.shape[0]]},
                    title={'text': service['service_name']},
                    gauge={
                        'axis': {'range': [None, 1]},
                        'bar': {'color': color},
                        'steps': [
                            {'range': [0, 1], 'color': "lightgray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 0.5
                        }
                    }
                ))
            
            fig_services.update_layout(height=400, template="plotly_white")
            st.plotly_chart(fig_services, use_container_width=True)
    
    with col2:
        st.markdown("##### 资源使用情况")
        resource_data = get_resource_usage()
        if not resource_data.empty:
            fig_resource = go.Figure()
            
            fig_resource.add_trace(go.Scatter(
                x=resource_data['timestamp'],
                y=resource_data['cpu_usage'],
                mode='lines',
                name='CPU使用率',
                line=dict(color='#1f77b4')
            ))
            
            fig_resource.add_trace(go.Scatter(
                x=resource_data['timestamp'],
                y=resource_data['memory_usage'],
                mode='lines',
                name='内存使用率',
                line=dict(color='#ff7f0e')
            ))
            
            fig_resource.update_layout(
                title="系统资源使用趋势",
                xaxis_title="时间",
                yaxis_title="使用率 (%)",
                height=400,
                template="plotly_white"
            )
            st.plotly_chart(fig_resource, use_container_width=True)
    
    # 数据库性能指标
    st.markdown("##### 数据库性能")
    db_metrics = get_database_metrics()
    if not db_metrics.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("查询响应时间", f"{db_metrics['avg_query_time'].iloc[0]:.2f}ms")
        with col2:
            st.metric("连接数", f"{db_metrics['active_connections'].iloc[0]}")
        with col3:
            st.metric("缓存命中率", f"{db_metrics['cache_hit_rate'].iloc[0]:.1f}%")
        with col4:
            st.metric("慢查询数", db_metrics['slow_queries'].iloc[0])

def render_runtime_logs():
    """渲染运行日志"""
    st.subheader("📝 系统运行日志")
    
    # 日志筛选
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        log_level = st.selectbox("日志级别", ["全部", "INFO", "WARNING", "ERROR", "DEBUG"])
    with col2:
        service_filter = st.selectbox("服务模块", ["全部", "数据采集", "数据处理", "数据存储", "API服务"])
    with col3:
        time_range = st.selectbox("时间范围", ["最近1小时", "最近6小时", "最近24小时", "最近7天"])
    with col4:
        search_keyword = st.text_input("搜索关键词", placeholder="输入关键词搜索")
    
    # 获取日志数据
    log_df = get_system_logs()
    
    if not log_df.empty:
        # 应用筛选
        if log_level != "全部":
            log_df = log_df[log_df['level'] == log_level]
        if service_filter != "全部":
            log_df = log_df[log_df['service'] == service_filter]
        if search_keyword:
            log_df = log_df[log_df['message'].str.contains(search_keyword, case=False, na=False)]
        
        st.markdown(f"**筛选结果**: 共 `{len(log_df)}` 条日志")
        
        # 日志级别分布
        col1, col2 = st.columns([1, 2])
        with col1:
            level_counts = log_df['level'].value_counts()
            fig_level = px.pie(
                values=level_counts.values,
                names=level_counts.index,
                title="日志级别分布",
                color_discrete_map={'ERROR': '#DC143C', 'WARNING': '#FFD700', 'INFO': '#1f77b4', 'DEBUG': '#2E8B57'}
            )
            fig_level.update_layout(height=300)
            st.plotly_chart(fig_level, use_container_width=True)
        
        with col2:
            # 实时日志流
            st.markdown("##### 实时日志流")
            
            # 日志表格
            st.dataframe(
                log_df.head(20),  # 显示最近20条
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("时间", format="HH:mm:ss"),
                    "level": st.column_config.TextColumn("级别", width="small"),
                    "service": st.column_config.TextColumn("服务", width="medium"),
                    "message": st.column_config.TextColumn("消息", width="large")
                },
                use_container_width=True,
                hide_index=True
            )
        
        # 日志导出
        if st.button("📥 导出日志"):
            csv_data = log_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="下载CSV日志文件",
                data=csv_data,
                file_name=f"system_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime='text/csv'
            )
    else:
        st.info("暂无日志数据")

def render_error_monitoring():
    """渲染异常监控"""
    st.subheader("⚠️ 异常监控与告警")
    
    # 异常统计
    error_stats = get_error_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("今日异常", error_stats.get('today_errors', 0), f"+{error_stats.get('error_increase', 0)} vs 昨日")
    with col2:
        st.metric("待处理", error_stats.get('pending_errors', 0), f"优先处理")
    with col3:
        st.metric("已解决", error_stats.get('resolved_errors', 0), f"处理率 {error_stats.get('resolution_rate', 0):.1f}%")
    with col4:
        st.metric("平均解决时间", f"{error_stats.get('avg_resolution_time', 0)}分钟")
    
    st.divider()
    
    # 异常趋势图
    col1, col2 = st.columns(2)
    with col1:
        error_trend = get_error_trend()
        if not error_trend.empty:
            fig_trend = px.line(
                error_trend,
                x='date',
                y='error_count',
                title="异常趋势（近7天）",
                labels={'date': '日期', 'error_count': '异常数量'}
            )
            fig_trend.update_layout(height=300)
            st.plotly_chart(fig_trend, use_container_width=True)
    
    with col2:
        error_types = get_error_types()
        if not error_types.empty:
            fig_types = px.bar(
                error_types,
                x='error_type',
                y='count',
                title="异常类型分布",
                labels={'error_type': '异常类型', 'count': '数量'}
            )
            fig_types.update_layout(height=300)
            st.plotly_chart(fig_types, use_container_width=True)
    
    # 异常详情列表
    st.markdown("##### 异常详情")
    error_logs = get_error_logs()
    if not error_logs.empty:
        st.dataframe(
            error_logs,
            column_config={
                "timestamp": st.column_config.DatetimeColumn("发生时间", format="MM-DD HH:mm:ss"),
                "error_type": st.column_config.TextColumn("异常类型", width="medium"),
                "severity": st.column_config.SelectboxColumn("严重程度", options=["低", "中", "高", "紧急"]),
                "message": st.column_config.TextColumn("异常信息", width="large"),
                "status": st.column_config.SelectboxColumn("处理状态", options=["待处理", "处理中", "已解决"]),
                "assigned_to": st.column_config.TextColumn("负责人", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ 当前无异常记录")

def render_performance_analysis():
    """渲染性能分析"""
    st.subheader("📈 系统性能分析")
    
    # 性能指标概览
    perf_metrics = get_performance_metrics()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("平均响应时间", f"{perf_metrics.get('avg_response_time', 0):.2f}ms")
    with col2:
        st.metric("请求成功率", f"{perf_metrics.get('success_rate', 0):.1f}%")
    with col3:
        st.metric("并发用户数", perf_metrics.get('concurrent_users', 0))
    
    st.divider()
    
    # 响应时间趋势
    response_trend = get_response_time_trend()
    if not response_trend.empty:
        fig_response = px.line(
            response_trend,
            x='timestamp',
            y='response_time',
            title="API响应时间趋势",
            labels={'timestamp': '时间', 'response_time': '响应时间 (ms)'}
        )
        fig_response.update_layout(height=350)
        st.plotly_chart(fig_response, use_container_width=True)
    
    # 吞吐量分析
    throughput_data = get_throughput_analysis()
    if not throughput_data.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig_throughput = px.bar(
                throughput_data,
                x='hour',
                y='request_count',
                title="每小时请求量分布",
                labels={'hour': '小时', 'request_count': '请求数'}
            )
            fig_throughput.update_layout(height=300)
            st.plotly_chart(fig_throughput, use_container_width=True)
        
        with col2:
            # API端点性能
            endpoint_performance = get_endpoint_performance()
            if not endpoint_performance.empty:
                fig_endpoint = px.scatter(
                    endpoint_performance,
                    x='avg_response_time',
                    y='request_count',
                    size='error_rate',
                    color='endpoint',
                    title="API端点性能分析",
                    labels={'avg_response_time': '平均响应时间', 'request_count': '请求数', 'error_rate': '错误率'}
                )
                fig_endpoint.update_layout(height=300)
                st.plotly_chart(fig_endpoint, use_container_width=True)

def render_log_search():
    """渲染日志查询"""
    st.subheader("🔍 高级日志查询")
    
    with st.form("advanced_search"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 查询条件")
            start_time = st.datetime_input("开始时间", value=datetime.now() - timedelta(hours=24))
            end_time = st.datetime_input("结束时间", value=datetime.now())
            selected_levels = st.multiselect(
                "日志级别",
                ["INFO", "WARNING", "ERROR", "DEBUG"],
                default=["WARNING", "ERROR"]
            )
            selected_services = st.multiselect(
                "服务模块",
                ["数据采集", "数据处理", "数据存储", "API服务"],
                default=["数据采集", "数据处理"]
            )
        
        with col2:
            st.markdown("#### 高级选项")
            keyword = st.text_input("关键词搜索", placeholder="支持正则表达式")
            exclude_keyword = st.text_input("排除关键词", placeholder="排除包含此关键词的日志")
            user_filter = st.text_input("用户筛选", placeholder="按用户ID筛选")
            session_filter = st.text_input("会话筛选", placeholder="按会话ID筛选")
        
        max_results = st.number_input("最大结果数", min_value=10, max_value=1000, value=100)
        
        search_button = st.form_submit_button("🔍 执行查询", type="primary")
    
    if search_button:
        with st.spinner("正在搜索日志..."):
            # 这里应该调用实际的搜索函数
            search_results = perform_advanced_log_search(
                start_time, end_time, selected_levels, selected_services,
                keyword, exclude_keyword, user_filter, session_filter, max_results
            )
            
            if not search_results.empty:
                st.success(f"✅ 搜索完成，找到 {len(search_results)} 条记录")
                
                # 搜索结果统计
                col1, col2, col3 = st.columns(3)
                with col1:
                    level_dist = search_results['level'].value_counts()
                    st.write("**级别分布:**")
                    for level, count in level_dist.items():
                        st.write(f"- {level}: {count}")
                
                with col2:
                    service_dist = search_results['service'].value_counts()
                    st.write("**服务分布:**")
                    for service, count in service_dist.head(5).items():
                        st.write(f"- {service}: {count}")
                
                with col3:
                    st.write("**时间分布:**")
                    hourly_dist = search_results.groupby(search_results['timestamp'].dt.hour).size()
                    for hour, count in hourly_dist.items():
                        st.write(f"- {hour:02d}:00 - {count} 条")
                
                # 详细结果
                st.dataframe(
                    search_results,
                    column_config={
                        "timestamp": st.column_config.DatetimeColumn("时间", format="YYYY-MM-DD HH:mm:ss"),
                        "level": st.column_config.TextColumn("级别", width="small"),
                        "service": st.column_config.TextColumn("服务", width="medium"),
                        "user": st.column_config.TextColumn("用户", width="small"),
                        "session": st.column_config.TextColumn("会话", width="medium"),
                        "message": st.column_config.TextColumn("消息", width="large")
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # 导出搜索结果
                csv_data = search_results.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 导出搜索结果",
                    data=csv_data,
                    file_name=f"log_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime='text/csv'
                )
            else:
                st.warning("⚠️ 未找到符合条件的日志记录")

# 辅助函数
@st.cache_data(ttl=60)
def get_system_stats():
    """获取系统统计信息"""
    return {
        'db_status': '正常',
        'db_pool_size': 8,
        'db_pool_max': 20,
        'collection_delay': 12,
        'delay_change': -3,
        'error_count': 5,
        'resolved_errors': 8,
        'data_throughput': 45,
        'throughput_change': 12.5
    }

@st.cache_data(ttl=300)
def get_service_status():
    """获取服务状态"""
    data = {
        'service_name': ['数据采集服务', '数据处理服务', '数据存储服务', 'API网关', 'Web前端'],
        'status': ['运行中', '运行中', '运行中', '运行中', '运行中']
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=60)
def get_resource_usage():
    """获取资源使用情况"""
    import pandas as pd
    times = pd.date_range(end=datetime.now(), periods=60, freq='min')
    cpu_usage = [30 + i*0.5 + (i%5)*2 for i in range(60)]
    memory_usage = [45 + i*0.3 + (i%7)*1.5 for i in range(60)]
    return pd.DataFrame({'timestamp': times, 'cpu_usage': cpu_usage, 'memory_usage': memory_usage})

@st.cache_data(ttl=300)
def get_database_metrics():
    """获取数据库性能指标"""
    data = {
        'avg_query_time': [2.5],
        'active_connections': [15],
        'cache_hit_rate': [94.2],
        'slow_queries': [3]
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_error_statistics():
    """获取异常统计"""
    return {
        'today_errors': 12,
        'error_increase': 3,
        'pending_errors': 5,
        'resolved_errors': 18,
        'resolution_rate': 78.3,
        'avg_resolution_time': 45
    }

@st.cache_data(ttl=300)
def get_error_trend():
    """获取异常趋势"""
    import pandas as pd
    dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
    counts = [8, 12, 6, 15, 9, 11, 12]
    return pd.DataFrame({'date': dates, 'error_count': counts})

@st.cache_data(ttl=300)
def get_error_types():
    """获取异常类型"""
    data = {
        'error_type': ['数据库连接', '网络超时', '数据格式', '权限验证', '系统资源'],
        'count': [3, 4, 2, 1, 2]
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_response_time_trend():
    """获取响应时间趋势"""
    import pandas as pd
    times = pd.date_range(end=datetime.now(), periods=24, freq='H')
    response_times = [15 + i*0.2 + (i%4)*3 for i in range(24)]
    return pd.DataFrame({'timestamp': times, 'response_time': response_times})

@st.cache_data(ttl=300)
def get_throughput_analysis():
    """获取吞吐量分析"""
    data = {
        'hour': list(range(24)),
        'request_count': [120, 95, 80, 65, 70, 150, 280, 350, 420, 380, 350, 320, 
                         340, 360, 390, 410, 380, 320, 280, 220, 180, 160, 140, 130]
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_endpoint_performance():
    """获取端点性能"""
    data = {
        'endpoint': ['/api/vitals', '/api/patients', '/api/devices', '/api/logs', '/api/mappings'],
        'avg_response_time': [12, 18, 25, 15, 22],
        'request_count': [1250, 890, 450, 320, 180],
        'error_rate': [0.5, 1.2, 0.8, 0.3, 1.5]
    }
    return pd.DataFrame(data)

def perform_advanced_log_search(start_time, end_time, levels, services, keyword, exclude, user, session, max_results):
    """执行高级日志搜索"""
    # 模拟搜索结果
    import pandas as pd
    import random
    
    results = []
    for i in range(min(max_results, 50)):  # 最多返回50条模拟数据
        timestamp = start_time + timedelta(minutes=random.randint(0, int((end_time - start_time).total_seconds() / 60)))
        results.append({
            'timestamp': timestamp,
            'level': random.choice(levels) if levels else random.choice(['INFO', 'WARNING', 'ERROR']),
            'service': random.choice(services) if services else random.choice(['数据采集', '数据处理']),
            'user': user if user else f"user_{random.randint(1, 10)}",
            'session': session if session else f"session_{random.randint(1000, 9999)}",
            'message': f"模拟日志消息 {i+1} - {keyword if keyword else '系统运行正常'}"
        })
    
    return pd.DataFrame(results)