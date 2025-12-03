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
        "SELECT TOP 1 patient_name, age, sex, hospital_id, bed_no, collection_location FROM cvsc_sign_main WHERE patient_id = :pid ORDER BY collection_time DESC",
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