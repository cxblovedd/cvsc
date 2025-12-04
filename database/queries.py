import streamlit as st
import pandas as pd
from sqlalchemy import text, exc
import logging
from datetime import datetime
from .connection import get_db_engine
from config import config

logger = logging.getLogger(__name__)

def run_query(query, params=None):
    """执行查询，返回 DataFrame"""
    try:
        with get_db_engine().connect() as conn:
            result = pd.read_sql(text(query), conn, params=params or {})
        return result
    except exc.SQLAlchemyError as e:
        logger.error(f"查询失败: {e}")
        st.error(f"查询失败: {str(e)}")
        return pd.DataFrame()

def run_update(sql, params=None):
    """执行更新/插入/删除"""
    try:
        with get_db_engine().begin() as conn:
            conn.execute(text(sql), params or {})
        return True
    except exc.SQLAlchemyError as e:
        logger.error(f"更新失败: {e}")
        st.error(f"更新失败: {str(e)}")
        return False

@st.cache_data(ttl=config.FILTER_CACHE_TTL)
def get_filter_options():
    """获取筛选条件的下拉选项（缓存以提高性能）"""
    try:
        # 获取所有出现过的科室/位置
        locs = run_query("SELECT DISTINCT collection_location FROM cvsc_sign_main WHERE collection_location IS NOT NULL")
        # 获取就诊类型
        types = run_query("SELECT DISTINCT patient_type FROM cvsc_sign_main WHERE patient_type IS NOT NULL")
        
        return {
            "locations": locs['collection_location'].tolist() if not locs.empty else [],
            "types": types['patient_type'].tolist() if not types.empty else []
        }
    except:
        return {"locations": [], "types": []}

@st.cache_data(ttl=config.QUERY_CACHE_TTL)
def get_standard_fields():
    """获取标准体征字段配置"""
    return run_query("SELECT id, field_name, description, unit FROM cvsc_standard_sign_config ORDER BY id")

@st.cache_data(ttl=config.QUERY_CACHE_TTL)
def get_device_models():
    """获取设备型号配置"""
    return run_query("SELECT id, model_name, manufacturer FROM cvsc_device_model_config ORDER BY model_name")

def search_patients(name=None, pid=None, bed_no=None, location=None, p_type=None):
    """多维度患者查询"""
    base_sql = """
        SELECT TOP 100
            m.patient_id, m.patient_name, m.sex, m.age, 
            m.bed_no, m.collection_location, m.patient_type,
            MAX(m.collection_time) as last_time
        FROM cvsc_sign_main m
        WHERE 1=1
    """
    params = {}
    
    if pid:
        base_sql += " AND m.patient_id LIKE :pid"
        params['pid'] = f"%{pid}%"
    if name:
        base_sql += " AND (m.patient_name LIKE :name OR m.patient_id LIKE :name)"
        params['name'] = f"%{name}%"
    if bed_no:
        base_sql += " AND m.bed_no = :bed_no"
        params['bed_no'] = bed_no
    if location and location != "全部":
        base_sql += " AND m.collection_location = :location"
        params['location'] = location
    if p_type and p_type != "全部":
        base_sql += " AND m.patient_type = :ptype"
        params['ptype'] = p_type
        
    base_sql += " GROUP BY m.patient_id, m.patient_name, m.sex, m.age, m.bed_no, m.collection_location, m.patient_type ORDER BY last_time DESC"
    
    return run_query(base_sql, params)

def build_time_filter_sql(start_time, end_time):
    """构建时间筛选SQL"""
    if start_time and end_time:
        return f"AND m.collection_time BETWEEN '{start_time.strftime('%Y-%m-%d %H:%M:%S')}' AND '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'"
    return ""

def query_vital_signs_paginated(patient_id, start_time, end_time):
    """查询生命体征详细数据"""
    time_filter = build_time_filter_sql(start_time, end_time)
    
    sql = f"""
    SELECT 
        m.collection_time,
        d.standard_field_id,
        d.standard_field_value,
        s.field_name,
        s.description,
        s.unit,
        s.normal_range_low,
        s.normal_range_high,
        s.warning_threshold
    FROM cvsc_sign_main m
    JOIN cvsc_sign_detail d ON m.id = d.vital_sign_data_id
    JOIN cvsc_standard_sign_config s ON d.standard_field_id = s.id
    WHERE m.patient_id = :pid
    {time_filter}
    ORDER BY m.collection_time DESC, d.standard_field_id
    """
    return run_query(sql, {"pid": patient_id})

def get_patient_basic_info(patient_id):
    """获取患者基本信息"""
    return run_query(
        "SELECT TOP 1 patient_id, patient_name, age, sex, hospital_id, bed_no, collection_location FROM cvsc_sign_main WHERE patient_id = :pid ORDER BY collection_time DESC",
        {"pid": patient_id}
    )

def get_dashboard_stats():
    """获取仪表板统计数据"""
    try:
        today_count = run_query("SELECT COUNT(*) as c FROM cvsc_sign_main WHERE CAST(collection_time AS DATE) = CAST(GETDATE() AS DATE)")
        device_count = run_query("SELECT COUNT(*) as c FROM mr_monitor_info")
        
        return {
            "today_collections": today_count['c'].values[0] if not today_count.empty else 0,
            "online_devices": device_count['c'].values[0] if not device_count.empty else 0
        }
    except:
        return {"today_collections": 0, "online_devices": 0}

def get_device_list():
    """获取设备列表"""
    return run_query("""
        SELECT id, monitor_code, monitor_name, mac, monitor_status, use_status, update_time
        FROM mr_monitor_info ORDER BY id DESC
    """)

def add_device(code, name, mac, status):
    """添加新设备"""
    sql = "INSERT INTO mr_monitor_info (monitor_code, monitor_name, mac, use_status, operate_time) VALUES (:c, :n, :m, :s, GETDATE())"
    return run_update(sql, {'c': code, 'n': name, 'm': mac, 's': status})

def get_field_mappings():
    """获取字段映射配置"""
    return run_query("""
        SELECT m.id, dm.model_name, m.device_field_name, s.description, m.conversion_formula
        FROM cvsc_device_field_rel m
        LEFT JOIN cvsc_device_model_config dm ON m.model_id = dm.id
        LEFT JOIN cvsc_standard_sign_config s ON m.standard_field_id = s.id
    """)

def add_field_mapping(model_id, standard_field_id, device_field_name, formula):
    """添加字段映射"""
    sql = "INSERT INTO cvsc_device_field_rel (model_id, standard_field_id, device_field_name, conversion_formula) VALUES (:m, :s, :d, :f)"
    return run_update(sql, {'m': model_id, 's': standard_field_id, 'd': device_field_name, 'f': formula})

def get_system_logs():
    """获取系统日志"""
    return run_query("""
        SELECT TOP 50 collection_time, patient_id, device_id, data_status 
        FROM cvsc_sign_main ORDER BY collection_time DESC
    """)

def get_device_stats():
    """获取设备统计数据"""
    try:
        total_devices = run_query("SELECT COUNT(*) as c FROM mr_monitor_info")
        online_devices = run_query("SELECT COUNT(*) as c FROM mr_monitor_info WHERE monitor_status = '在线'")
        in_use_devices = run_query("SELECT COUNT(*) as c FROM mr_monitor_info WHERE use_status = '使用中'")
        
        return {
            'total_devices': total_devices['c'].values[0] if not total_devices.empty else 0,
            'online_devices': online_devices['c'].values[0] if not online_devices.empty else 0,
            'in_use_devices': in_use_devices['c'].values[0] if not in_use_devices.empty else 0,
            'online_rate': (online_devices['c'].values[0] / total_devices['c'].values[0] * 100) if not total_devices.empty and total_devices['c'].values[0] > 0 else 0,
            'usage_rate': (in_use_devices['c'].values[0] / total_devices['c'].values[0] * 100) if not total_devices.empty and total_devices['c'].values[0] > 0 else 0,
            'maintenance_needed': run_query("SELECT COUNT(*) as c FROM mr_monitor_info WHERE use_status = '维护中'")['c'].values[0] if not run_query("SELECT COUNT(*) as c FROM mr_monitor_info WHERE use_status = '维护中'").empty else 0,
            'new_devices_this_month': 30,  # 模拟数据
            'resolved_today': 5  # 模拟数据
        }
    except:
        return {
            'total_devices': 0, 'online_devices': 0, 'in_use_devices': 0,
            'online_rate': 0, 'usage_rate': 0, 'maintenance_needed': 0,
            'new_devices_this_month': 0, 'resolved_today': 0
        }

def get_mapping_stats():
    """获取映射统计数据"""
    try:
        total_mappings = run_query("SELECT COUNT(*) as c FROM cvsc_device_field_rel")
        device_models = run_query("SELECT COUNT(DISTINCT model_id) as c FROM cvsc_device_field_rel")
        standard_fields = run_query("SELECT COUNT(*) as c FROM cvsc_standard_sign_config")
        mapped_fields = run_query("SELECT COUNT(DISTINCT standard_field_id) as c FROM cvsc_device_field_rel")
        
        return {
            'total_mappings': total_mappings['c'].values[0] if not total_mappings.empty else 0,
            'device_models': device_models['c'].values[0] if not device_models.empty else 0,
            'standard_fields': standard_fields['c'].values[0] if not standard_fields.empty else 0,
            'mapped_fields': mapped_fields['c'].values[0] if not mapped_fields.empty else 0,
            'new_mappings_today': 3,  # 模拟数据
            'active_models': device_models['c'].values[0] if not device_models.empty else 0,
            'pending_validation': 5,  # 模拟数据
            'validated_today': 8  # 模拟数据
        }
    except:
        return {
            'total_mappings': 0, 'device_models': 0, 'standard_fields': 0,
            'mapped_fields': 0, 'new_mappings_today': 0, 'active_models': 0,
            'pending_validation': 0, 'validated_today': 0
        }

def delete_field_mapping(mapping_id):
    """删除字段映射"""
    return run_update("DELETE FROM cvsc_device_field_rel WHERE id = :id", {'id': mapping_id})

def update_field_mapping(mapping_id, **kwargs):
    """更新字段映射"""
    set_clauses = []
    params = {'id': mapping_id}
    
    for key, value in kwargs.items():
        if value is not None:
            set_clauses.append(f"{key} = :{key}")
            params[key] = value
    
    if set_clauses:
        sql = f"UPDATE cvsc_device_field_rel SET {', '.join(set_clauses)} WHERE id = :id"
        return run_update(sql, params)
    return False

def get_error_logs():
    """获取错误日志"""
    # 模拟数据，实际应该从日志表查询
    import pandas as pd
    from datetime import datetime, timedelta
    
    data = []
    for i in range(10):
        data.append({
            'timestamp': datetime.now() - timedelta(hours=i),
            'error_type': ['数据库连接', '网络超时', '数据格式', '权限验证'][i % 4],
            'severity': ['低', '中', '高', '紧急'][i % 4],
            'message': f'模拟错误消息 {i+1}',
            'status': ['待处理', '处理中', '已解决'][i % 3],
            'assigned_to': [None, '张工', '李工'][i % 3]
        })
    
    return pd.DataFrame(data)

def get_performance_metrics():
    """获取性能指标"""
    return {
        'avg_response_time': 25.5,
        'success_rate': 98.7,
        'concurrent_users': 45
    }

def get_system_stats():
    """获取系统统计数据"""
    try:
        today_count = run_query("SELECT COUNT(*) as c FROM cvsc_sign_main WHERE CAST(collection_time AS DATE) = CAST(GETDATE() AS DATE)")
        device_count = run_query("SELECT COUNT(*) as c FROM mr_monitor_info WHERE monitor_status = '在线'")
        
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
    except:
        return {
            'db_status': '异常',
            'db_pool_size': 0,
            'db_pool_max': 20,
            'collection_delay': 0,
            'delay_change': 0,
            'error_count': 0,
            'resolved_errors': 0,
            'data_throughput': 0,
            'throughput_change': 0
        }

def get_active_alerts():
    """获取活跃告警"""
    # 模拟告警数据
    import pandas as pd
    from datetime import datetime, timedelta
    
    alerts_data = []
    patient_names = ['张三', '李四', '王五', '赵六', '钱七']
    bed_numbers = ['ICU-01', 'ICU-02', '内科-15', '外科-08', '急诊-02']
    messages = [
        '心率异常：过高 (>120)',
        '血氧饱和度偏低：(<92%)',
        '体温异常：发热 (>38.5°C)',
        '血压异常：收缩压过高 (>160)',
        '呼吸频率异常：过快 (>25)'
    ]
    severities = ['危急', '警告', '提示']
    
    for i in range(8):  # 生成8条告警
        alerts_data.append({
            'id': i + 1,
            'patient_id': f'P{1000 + i}',
            'patient_name': patient_names[i % len(patient_names)],
            'bed_no': bed_numbers[i % len(bed_numbers)],
            'message': messages[i % len(messages)],
            'severity': severities[i % len(severities)],
            'timestamp': datetime.now() - timedelta(minutes=i*15)
        })
    
    return pd.DataFrame(alerts_data)

def get_device_monitoring_stats():
    """获取设备监控统计"""
    # 模拟设备状态数据
    import pandas as pd
    
    data = {
        'status': ['在线', '离线', '维护'],
        'count': [42, 5, 3]
    }
    return pd.DataFrame(data)

def get_device_performance_metrics():
    """获取设备性能指标"""
    return {
        'avg_response_time': 25,
        'success_rate': 98.5,
        'failure_rate': 1.5,
        'scheduled_maintenance': 2
    }