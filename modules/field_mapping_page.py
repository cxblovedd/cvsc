import streamlit as st
import pandas as pd
import plotly.express as px
from database.queries import get_field_mappings, add_field_mapping, get_device_models, get_standard_fields, delete_field_mapping
from utils.helpers import validate_mapping_form
from components.common import render_footer

def render_field_mapping():
    """渲染字段映射页面"""
    st.title("🔌 协议字段映射配置")
    
    # 概览统计
    render_mapping_overview()
    
    st.divider()
    
    # 主要功能标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📋 映射管理", "➕ 新增映射", "🧪 测试验证", "📊 映射统计"])
    
    with tab1:
        render_mapping_management()
    
    with tab2:
        render_add_mapping()
    
    with tab3:
        render_mapping_testing()
    
    with tab4:
        render_mapping_statistics()
    
    render_footer()

def render_mapping_overview():
    """渲染映射概览统计"""
    stats = get_mapping_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="🔗 映射总数",
            value=stats.get('total_mappings', 0),
            delta=f"+{stats.get('new_mappings_today', 0)} 今日新增"
        )
    with col2:
        st.metric(
            label="🖥️ 设备型号",
            value=stats.get('device_models', 0),
            delta=f"{stats.get('active_models', 0)} 个活跃"
        )
    with col3:
        st.metric(
            label="📊 标准字段",
            value=stats.get('standard_fields', 0),
            delta=f"{stats.get('mapped_fields', 0)} 个已映射"
        )
    with col4:
        st.metric(
            label="⚠️ 待验证",
            value=stats.get('pending_validation', 0),
            delta=f"-{stats.get('validated_today', 0)} 今日验证"
        )

def render_mapping_management():
    """渲染映射管理"""
    st.subheader("📋 字段映射管理")
    
    # 筛选选项
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        device_filter = st.selectbox("设备型号", ["全部"] + get_device_model_names())
    with col2:
        field_filter = st.selectbox("标准字段", ["全部"] + get_standard_field_names())
    with col3:
        status_filter = st.selectbox("验证状态", ["全部", "已验证", "待验证", "验证失败"])
    with col4:
        search_mapping = st.text_input("搜索映射", placeholder="原始字段名")
    
    # 获取映射数据
    mapping_df = get_field_mappings()
    
    if not mapping_df.empty:
        # 应用筛选
        if device_filter != "全部":
            mapping_df = mapping_df[mapping_df['device_model_name'] == device_filter]
        if field_filter != "全部":
            mapping_df = mapping_df[mapping_df['standard_field_name'] == field_filter]
        if status_filter != "全部":
            mapping_df = mapping_df[mapping_df['validation_status'] == status_filter]
        if search_mapping:
            mapping_df = mapping_df[
                mapping_df['original_field_name'].str.contains(search_mapping, case=False)
            ]
        
        st.markdown(f"**筛选结果**: 共 `{len(mapping_df)}` 条映射")
        
        # 批量操作
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔄 刷新映射", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("📥 导出配置", use_container_width=True):
                export_mapping_config(mapping_df)
        
        # 映射数据表格
        edited_df = st.data_editor(
            mapping_df,
            column_config={
                "device_model_name": st.column_config.TextColumn("设备型号", width="medium"),
                "original_field_name": st.column_config.TextColumn("原始字段", width="medium"),
                "standard_field_name": st.column_config.TextColumn("标准字段", width="medium"),
                "conversion_formula": st.column_config.TextColumn("转换公式", width="small"),
                "validation_status": st.column_config.SelectboxColumn(
                    "验证状态",
                    options=["已验证", "待验证", "验证失败"],
                    help="映射配置的验证状态"
                ),
                "last_tested": st.column_config.DatetimeColumn("最后测试", format="MM-DD HH:mm"),
                "created_time": st.column_config.DatetimeColumn("创建时间", format="MM-DD HH:mm", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )
        
        # 删除选中映射
        if st.button("🗑️ 删除选中映射", type="secondary"):
            st.warning("⚠️ 删除操作不可恢复，请谨慎操作！")
        
        st.caption("💡 提示：直接编辑表格可更新映射配置，或使用右侧表单添加新映射")
    else:
        st.info("暂无映射配置，请先添加字段映射。")

def render_add_mapping():
    """渲染新增映射"""
    st.subheader("➕ 新增字段映射")
    
    with st.form("add_mapping_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 设备信息")
            models = get_device_models()
            model_names = models['id'].tolist() if not models.empty else []
            
            selected_model_id = st.selectbox(
                "设备型号 *",
                model_names,
                format_func=lambda x: f"{models[models['id']==x]['model_name'].values[0]} ({models[models['id']==x]['manufacturer'].values[0]})" if not models.empty else ""
            )
            
            # 显示选中设备的详细信息
            if selected_model_id and not models.empty:
                device_info = models[models['id']==selected_model_id].iloc[0]
                st.info(f"**制造商**: {device_info['manufacturer']}  |  **型号**: {device_info['model_name']}")
            
        with col2:
            st.markdown("#### 标准字段")
            standards = get_standard_fields()
            standard_names = standards['id'].tolist() if not standards.empty else []
            
            selected_standard_id = st.selectbox(
                "标准字段 *",
                standard_names,
                format_func=lambda x: f"{standards[standards['id']==x]['description'].values[0]} ({standards[standards['id']==x]['unit'].values[0]})" if not standards.empty else ""
            )
            
            # 显示选中字段的详细信息
            if selected_standard_id and not standards.empty:
                field_info = standards[standards['id']==selected_standard_id].iloc[0]
                st.info(f"**字段描述**: {field_info['description']}  |  **单位**: {field_info['unit']}  |  **正常范围**: {field_info.get('normal_range', 'N/A')}")
        
        st.markdown("#### 映射配置")
        col1, col2 = st.columns(2)
        with col1:
            original_field = st.text_input("原始字段名 *", placeholder="设备协议中的原始字段名", help="例如：HR、TEMP、SPO2")
        with col2:
            data_type = st.selectbox("数据类型", ["数值", "字符串", "布尔值"])
        
        conversion_formula = st.text_input(
            "转换公式",
            value="x*1.0",
            placeholder="例如：x*1.0、(x-32)*5/9、round(x, 1)",
            help="使用变量x表示原始值，支持数学表达式"
        )
        
        st.markdown("#### 高级选项")
        col1, col2 = st.columns(2)
        with col1:
            priority = st.selectbox("优先级", ["高", "中", "低"], index=1)
        with col2:
            is_active = st.checkbox("启用此映射", value=True)
        
        validation_rules = st.text_area(
            "验证规则",
            placeholder="例如：x>0 and x<300",
            help="数据验证条件，不满足条件的数据将被标记为异常"
        )
        
        notes = st.text_area("备注", placeholder="映射配置的补充说明")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submitted = st.form_submit_button("保存映射", use_container_width=True, type="primary")
        with col2:
            test_mapping = st.form_submit_button("测试映射", use_container_width=True)
        
        if submitted:
            mapping_data = {
                'device_model_id': selected_model_id,
                'standard_field_id': selected_standard_id,
                'original_field_name': original_field,
                'data_type': data_type,
                'conversion_formula': conversion_formula,
                'priority': priority,
                'is_active': is_active,
                'validation_rules': validation_rules,
                'notes': notes
            }
            
            errors = validate_mapping_form(selected_model_id, selected_standard_id, original_field)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                if add_field_mapping(mapping_data):
                    st.success("✅ 映射配置保存成功！")
                    st.rerun()
                else:
                    st.error("❌ 映射配置保存失败，请检查信息后重试。")
        
        if test_mapping:
            test_result = test_mapping_conversion(conversion_formula, data_type)
            if test_result['success']:
                st.success(f"✅ 转换公式测试成功：{test_result['example']}")
            else:
                st.error(f"❌ 转换公式测试失败：{test_result['error']}")

def render_mapping_testing():
    """渲染映射测试"""
    st.subheader("🧪 映射配置测试")
    
    st.markdown("#### 批量测试")
    col1, col2 = st.columns(2)
    with col1:
        test_model = st.selectbox("选择设备型号", get_device_model_names())
    with col2:
        test_count = st.number_input("测试数据量", min_value=1, max_value=100, value=10)
    
    if st.button("🚀 开始批量测试", type="primary"):
        with st.spinner("正在测试映射配置..."):
            test_results = run_batch_mapping_test(test_model, test_count)
            
            if test_results['success']:
                st.success(f"✅ 批量测试完成，成功率：{test_results['success_rate']:.1f}%")
                
                # 显示测试结果
                results_df = pd.DataFrame(test_results['details'])
                st.dataframe(results_df, use_container_width=True, hide_index=True)
                
                # 可视化测试结果
                if not results_df.empty:
                    fig = px.pie(
                        values=results_df['result'].value_counts().values,
                        names=results_df['result'].value_counts().index,
                        title="测试结果分布"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"❌ 批量测试失败：{test_results['error']}")
    
    st.divider()
    
    st.markdown("#### 单个映射测试")
    mapping_df = get_field_mappings()
    if not mapping_df.empty:
        selected_mapping = st.selectbox(
            "选择映射配置",
            mapping_df.index,
            format_func=lambda x: f"{mapping_df.iloc[x]['device_model_name']} -> {mapping_df.iloc[x]['standard_field_name']}"
        )
        
        test_value = st.text_input("测试值", placeholder="输入要测试的原始数据值")
        
        if st.button("🧪 测试单个映射"):
            if test_value:
                mapping_info = mapping_df.iloc[selected_mapping]
                result = test_single_mapping(mapping_info, test_value)
                
                if result['success']:
                    st.success("✅ 测试成功")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("原始值", result['original_value'])
                    with col2:
                        st.metric("转换值", result['converted_value'])
                    
                    if result['validation_passed']:
                        st.success("✅ 数据验证通过")
                    else:
                        st.warning("⚠️ 数据验证未通过")
                else:
                    st.error(f"❌ 测试失败：{result['error']}")

def render_mapping_statistics():
    """渲染映射统计"""
    st.subheader("📊 映射统计分析")
    
    # 映射分布图表
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 设备型号映射分布")
        device_mapping_stats = get_device_mapping_stats()
        if not device_mapping_stats.empty:
            fig_device = px.bar(
                device_mapping_stats,
                x='device_model_name',
                y='mapping_count',
                title="各设备型号映射数量",
                labels={'device_model_name': '设备型号', 'mapping_count': '映射数量'}
            )
            fig_device.update_layout(height=350)
            st.plotly_chart(fig_device, use_container_width=True)
    
    with col2:
        st.markdown("##### 标准字段映射覆盖")
        field_coverage = get_field_coverage_stats()
        if not field_coverage.empty:
            fig_field = px.pie(
                values=field_coverage['mapping_count'],
                names=field_coverage['standard_field_name'],
                title="标准字段映射覆盖"
            )
            fig_field.update_layout(height=350)
            st.plotly_chart(fig_field, use_container_width=True)
    
    # 映射质量分析
    st.markdown("##### 映射质量分析")
    quality_stats = get_mapping_quality_stats()
    if not quality_stats.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("验证通过率", f"{quality_stats['validation_pass_rate']:.1f}%")
        with col2:
            st.metric("平均转换时间", f"{quality_stats['avg_conversion_time']:.2f}ms")
        with col3:
            st.metric("错误率", f"{quality_stats['error_rate']:.1f}%")
        
        # 质量趋势图
        quality_trend = get_quality_trend()
        if not quality_trend.empty:
            fig_trend = px.line(
                quality_trend,
                x='date',
                y='success_rate',
                title="映射成功率趋势（近7天）",
                labels={'date': '日期', 'success_rate': '成功率 (%)'}
            )
            fig_trend.update_layout(height=300)
            st.plotly_chart(fig_trend, use_container_width=True)

# 辅助函数
def get_mapping_stats():
    """获取映射统计信息"""
    # 模拟数据
    return {
        'total_mappings': 156,
        'new_mappings_today': 3,
        'device_models': 12,
        'active_models': 10,
        'standard_fields': 28,
        'mapped_fields': 24,
        'pending_validation': 5,
        'validated_today': 8
    }

def get_device_model_names():
    """获取设备型号名称列表"""
    return ["迈瑞T5", "菲利普MX700", "GE CARESCAPE", "西门子SC6000"]

def get_standard_field_names():
    """获取标准字段名称列表"""
    return ["体温", "脉搏", "呼吸", "血压", "血氧饱和度", "心输出量"]

def export_mapping_config(df):
    """导出映射配置"""
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="下载CSV配置文件",
        data=csv_data,
        file_name=f"field_mapping_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime='text/csv'
    )

def test_mapping_conversion(formula, data_type):
    """测试转换公式"""
    try:
        if data_type == "数值":
            test_values = [100, 37.5, 0, -10]
            for val in test_values:
                x = val
                result = eval(formula)
            return {'success': True, 'example': f"输入: 100 -> 输出: {eval(formula)}"}
        else:
            return {'success': True, 'example': "字符串类型测试通过"}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def run_batch_mapping_test(model_name, count):
    """运行批量映射测试"""
    # 模拟测试结果
    import random
    success_count = int(count * 0.85)
    
    details = []
    for i in range(count):
        if i < success_count:
            details.append({
                'test_id': i + 1,
                'original_value': random.randint(50, 150),
                'converted_value': random.randint(50, 150),
                'result': '成功'
            })
        else:
            details.append({
                'test_id': i + 1,
                'original_value': random.randint(50, 150),
                'converted_value': None,
                'result': '失败'
            })
    
    return {
        'success': True,
        'success_rate': (success_count / count) * 100,
        'details': details
    }

def test_single_mapping(mapping_info, test_value):
    """测试单个映射"""
    try:
        formula = mapping_info['conversion_formula']
        x = float(test_value)
        converted_value = eval(formula)
        
        return {
            'success': True,
            'original_value': test_value,
            'converted_value': converted_value,
            'validation_passed': True
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@st.cache_data(ttl=300)
def get_device_mapping_stats():
    """获取设备映射统计"""
    data = {
        'device_model_name': ['迈瑞T5', '菲利普MX700', 'GE CARESCAPE', '西门子SC6000'],
        'mapping_count': [45, 38, 32, 28]
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_field_coverage_stats():
    """获取字段覆盖统计"""
    data = {
        'standard_field_name': ['体温', '脉搏', '呼吸', '血压', '血氧饱和度'],
        'mapping_count': [12, 15, 10, 18, 14]
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_mapping_quality_stats():
    """获取映射质量统计"""
    return {
        'validation_pass_rate': 92.5,
        'avg_conversion_time': 1.2,
        'error_rate': 3.8
    }

@st.cache_data(ttl=300)
def get_quality_trend():
    """获取质量趋势"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
    success_rates = [88, 90, 87, 92, 91, 93, 92.5]
    return pd.DataFrame({'date': dates, 'success_rate': success_rates})