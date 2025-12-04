import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from database.queries import get_device_list, add_device, get_device_models, get_standard_fields, get_device_stats
from utils.helpers import validate_device_form
from components.common import render_footer

def render_device_management():
    """渲染设备管理页面"""
    st.title("⚙️ 设备资产管理")
    
    # 设备统计概览
    render_device_overview()
    
    st.divider()
    
    # 主要功能标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📋 设备列表", "➕ 新增设备", "📊 设备统计", "🔧 维护记录"])
    
    with tab1:
        render_device_list()
    
    with tab2:
        render_add_device()
    
    with tab3:
        render_device_statistics()
    
    with tab4:
        render_maintenance_records()
    
    render_footer()

def render_device_overview():
    """渲染设备概览统计"""
    stats = get_device_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="🖥️ 设备总数",
            value=stats.get('total_devices', 0),
            delta=f"+{stats.get('new_devices_this_month', 0)} 本月新增"
        )
    with col2:
        st.metric(
            label="🟢 在线设备",
            value=stats.get('online_devices', 0),
            delta=f"{stats.get('online_rate', 0)}% 在线率"
        )
    with col3:
        st.metric(
            label="🔄 使用中",
            value=stats.get('in_use_devices', 0),
            delta=f"{stats.get('usage_rate', 0)}% 使用率"
        )
    with col4:
        st.metric(
            label="⚠️ 需维护",
            value=stats.get('maintenance_needed', 0),
            delta=f"-{stats.get('resolved_today', 0)} 今日已处理"
        )

def render_device_list():
    """渲染设备列表"""
    st.subheader("📋 设备库存管理")
    
    # 筛选选项
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_filter = st.selectbox("在线状态", ["全部", "在线", "离线"])
    with col2:
        use_filter = st.selectbox("使用状态", ["全部", "使用中", "空闲", "维护中"])
    with col3:
        location_filter = st.selectbox("所在位置", ["全部", "ICU", "内科", "外科", "急诊"])
    with col4:
        search_device = st.text_input("搜索设备", placeholder="输入编号或名称")
    
    # 获取设备数据
    df_devices = get_device_list()
    
    if not df_devices.empty:
        # 应用筛选
        if status_filter != "全部":
            df_devices = df_devices[df_devices['monitor_status'] == status_filter]
        if use_filter != "全部":
            df_devices = df_devices[df_devices['use_status'] == use_filter]
        if location_filter != "全部":
            df_devices = df_devices[df_devices['location'] == location_filter]
        if search_device:
            df_devices = df_devices[
                df_devices['monitor_code'].str.contains(search_device, case=False) |
                df_devices['monitor_name'].str.contains(search_device, case=False)
            ]
        
        st.markdown(f"**筛选结果**: 共 `{len(df_devices)}` 台设备")
        
        # 设备状态图表
        if not df_devices.empty:
            col1, col2 = st.columns(2)
            with col1:
                status_counts = df_devices['monitor_status'].value_counts()
                fig_status = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="设备在线状态分布",
                    color_discrete_map={'在线': '#2E8B57', '离线': '#DC143C'}
                )
                fig_status.update_layout(height=300)
                st.plotly_chart(fig_status, use_container_width=True)
            
            with col2:
                use_counts = df_devices['use_status'].value_counts()
                fig_use = px.bar(
                    x=use_counts.index,
                    y=use_counts.values,
                    title="设备使用状态分布",
                    labels={'x': '使用状态', 'y': '设备数量'},
                    color=use_counts.index,
                    color_discrete_map={'使用中': '#1f77b4', '空闲': '#2ca02c', '维护中': '#ff7f0e'}
                )
                fig_use.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_use, use_container_width=True)
        
        # 设备详细列表
        st.subheader("设备详细信息")
        
        # 添加批量操作
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔄 刷新状态", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("📥 导出列表", use_container_width=True):
                csv_data = df_devices.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="下载CSV",
                    data=csv_data,
                    file_name=f"device_list_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv'
                )
        
        # 设备数据表格
        edited_df = st.data_editor(
            df_devices,
            column_config={
                "monitor_code": st.column_config.TextColumn("设备编号", width="medium"),
                "monitor_name": st.column_config.TextColumn("设备名称", width="medium"),
                "monitor_status": st.column_config.SelectboxColumn(
                    "在线状态", 
                    options=["在线", "离线"],
                    help="设备当前网络连接状态"
                ),
                "use_status": st.column_config.SelectboxColumn(
                    "使用状态", 
                    options=["使用中", "空闲", "维护中"],
                    help="设备当前使用情况"
                ),
                "location": st.column_config.TextColumn("所在位置", width="small"),
                "last_heartbeat": st.column_config.DatetimeColumn("最后心跳", format="MM-DD HH:mm"),
                "update_time": st.column_config.DatetimeColumn("更新时间", format="MM-DD HH:mm", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )
        
        st.caption("💡 提示：直接编辑表格可更新设备状态，或点击行右侧的详情按钮查看更多信息")
    else:
        st.info("暂无设备数据，请先添加设备。")

def render_add_device():
    """渲染新增设备表单"""
    st.subheader("➕ 新增设备登记")
    
    with st.form("add_device_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 基本信息")
            code = st.text_input("设备编号 (SN) *", placeholder="请输入唯一设备序列号")
            name = st.text_input("设备名称/型号 *", placeholder="例如：迈瑞T5")
            manufacturer = st.selectbox("制造商", ["迈瑞", "菲利普", "GE", "西门子", "其他"])
            model = st.text_input("设备型号", placeholder="例如：T5、IntelliVue MX700")
            
        with col2:
            st.markdown("#### 网络信息")
            mac = st.text_input("MAC地址", placeholder="例如：00:11:22:33:44:55")
            ip = st.text_input("IP地址", placeholder="例如：192.168.1.100")
            location = st.selectbox("所在位置", ["ICU", "内科", "外科", "急诊", "儿科", "妇产科"])
            department = st.text_input("所属科室", placeholder="例如：重症医学科")
        
        st.markdown("#### 状态设置")
        col1, col2, col3 = st.columns(3)
        with col1:
            use_status = st.selectbox("初始使用状态", ["空闲", "使用中", "维护中"])
        with col2:
            warranty_end = st.date_input("保修到期日", value=datetime.now() + timedelta(days=365*3))
        with col3:
            responsible_person = st.text_input("负责人", placeholder="设备管理员姓名")
        
        st.markdown("#### 备注信息")
        notes = st.text_area("备注", placeholder="设备特殊说明、配置要求等")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submitted = st.form_submit_button("提交登记", use_container_width=True, type="primary")
        with col2:
            reset_form = st.form_submit_button("重置表单", use_container_width=True)
        
        if submitted:
            errors = validate_device_form(code, name, mac)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                device_data = {
                    'monitor_code': code,
                    'monitor_name': name,
                    'manufacturer': manufacturer,
                    'model': model,
                    'mac_address': mac,
                    'ip_address': ip,
                    'location': location,
                    'department': department,
                    'use_status': use_status,
                    'warranty_end': warranty_end,
                    'responsible_person': responsible_person,
                    'notes': notes
                }
                
                if add_device(device_data):
                    st.success("✅ 设备登记成功！")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ 设备登记失败，请检查信息后重试。")

def render_device_statistics():
    """渲染设备统计"""
    st.subheader("📊 设备统计分析")
    
    stats = get_device_stats()
    
    # 设备类型分布
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 设备制造商分布")
        manufacturer_data = get_manufacturer_stats()
        if not manufacturer_data.empty:
            fig_manufacturer = px.pie(
                values=manufacturer_data['count'],
                names=manufacturer_data['manufacturer'],
                title="设备制造商分布"
            )
            fig_manufacturer.update_layout(height=350)
            st.plotly_chart(fig_manufacturer, use_container_width=True)
    
    with col2:
        st.markdown("##### 设备使用率趋势")
        usage_trend = get_usage_trend()
        if not usage_trend.empty:
            fig_usage = px.line(
                usage_trend,
                x='date',
                y='usage_rate',
                title="设备使用率趋势（近7天）",
                labels={'date': '日期', 'usage_rate': '使用率 (%)'}
            )
            fig_usage.update_layout(height=350)
            st.plotly_chart(fig_usage, use_container_width=True)
    
    # 设备健康度评分
    st.markdown("##### 设备健康度评分")
    health_scores = get_device_health_scores()
    if not health_scores.empty:
        fig_health = px.bar(
            health_scores.head(10),  # 显示前10台设备
            x='monitor_code',
            y='health_score',
            color='health_status',
            title="设备健康度评分",
            labels={'monitor_code': '设备编号', 'health_score': '健康度评分', 'health_status': '健康状态'},
            color_discrete_map={'优秀': '#2E8B57', '良好': '#2ca02c', '一般': '#ff7f0e', '较差': '#DC143C'}
        )
        fig_health.update_layout(height=400)
        st.plotly_chart(fig_health, use_container_width=True)

def render_maintenance_records():
    """渲染维护记录"""
    st.subheader("🔧 设备维护记录")
    
    # 维护统计
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("本月维护", "12次", "+3次 vs 上月")
    with col2:
        st.metric("待处理", "3项", "需关注")
    with col3:
        st.metric("平均时长", "2.5小时", "-0.5小时")
    
    st.divider()
    
    # 维护记录表格
    maintenance_data = get_maintenance_records()
    if not maintenance_data.empty:
        st.dataframe(
            maintenance_data,
            column_config={
                "device_code": "设备编号",
                "maintenance_type": "维护类型",
                "start_time": st.column_config.DatetimeColumn("开始时间", format="MM-DD HH:mm"),
                "end_time": st.column_config.DatetimeColumn("结束时间", format="MM-DD HH:mm"),
                "duration": "耗时",
                "technician": "技术员",
                "status": "状态"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("暂无维护记录")

# 辅助函数
@st.cache_data(ttl=300)
def get_manufacturer_stats():
    """获取制造商统计"""
    # 模拟数据
    data = {
        'manufacturer': ['迈瑞', '菲利普', 'GE', '西门子'],
        'count': [15, 12, 8, 5]
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_usage_trend():
    """获取使用率趋势"""
    # 模拟数据
    dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
    usage_rates = [85, 88, 82, 90, 87, 92, 89]
    return pd.DataFrame({'date': dates, 'usage_rate': usage_rates})

@st.cache_data(ttl=300)
def get_device_health_scores():
    """获取设备健康度评分"""
    # 模拟数据
    data = {
        'monitor_code': [f'DEV{i:03d}' for i in range(1, 16)],
        'health_score': [95, 88, 92, 78, 85, 91, 73, 89, 94, 82, 87, 76, 90, 84, 88],
        'health_status': ['优秀', '良好', '优秀', '一般', '良好', '优秀', '较差', '良好', '优秀', '良好', '良好', '一般', '优秀', '良好', '良好']
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_maintenance_records():
    """获取维护记录"""
    # 模拟数据
    data = {
        'device_code': ['DEV001', 'DEV003', 'DEV007', 'DEV002', 'DEV005'],
        'maintenance_type': ['例行检查', '故障维修', '校准', '清洁保养', '软件升级'],
        'start_time': [datetime.now() - timedelta(hours=2), datetime.now() - timedelta(days=1), datetime.now() - timedelta(days=2), datetime.now() - timedelta(days=3), datetime.now() - timedelta(days=4)],
        'end_time': [datetime.now() - timedelta(hours=1), datetime.now() - timedelta(days=1, hours=1), datetime.now() - timedelta(days=2, hours=1), datetime.now() - timedelta(days=3, hours=1), datetime.now() - timedelta(days=4, hours=1)],
        'duration': ['1小时', '1小时', '1小时', '1小时', '1小时'],
        'technician': ['张工', '李工', '王工', '张工', '李工'],
        'status': ['已完成', '已完成', '已完成', '已完成', '已完成']
    }
    return pd.DataFrame(data)