import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from functools import lru_cache

def get_status_color(value, low_threshold, high_threshold):
    """根据阈值判断状态颜色"""
    if pd.notnull(high_threshold) and value > high_threshold: 
        return "🔴 偏高"
    if pd.notnull(low_threshold) and value < low_threshold: 
        return "🟠 偏低"
    return "🟢 正常"

def highlight_status_row(row):
    """根据状态高亮表格行"""
    if "偏高" in row.get('status_label', ''): 
        return ['background-color: #ffe6e6'] * len(row)
    if "偏低" in row.get('status_label', ''): 
        return ['background-color: #fff3cd'] * len(row)
    return [''] * len(row)

def calculate_time_range(range_name):
    """计算时间范围"""
    now = datetime.now()
    if range_name == "最近12小时":
        return now - timedelta(hours=12)
    elif range_name == "最近24小时":
        return now - timedelta(hours=24)
    elif range_name == "最近3天":
        return now - timedelta(days=3)
    elif range_name == "最近7天":
        return now - timedelta(days=7)
    else:
        return now - timedelta(hours=24)

@lru_cache(maxsize=128)
def format_patient_display(patient_id, patient_name):
    """格式化患者显示名称"""
    return f"{patient_id} - {patient_name}"

def validate_device_form(code, name, mac):
    """验证设备表单"""
    errors = []
    if not code.strip():
        errors.append("设备编号不能为空")
    if not name.strip():
        errors.append("设备名称不能为空")
    if not mac.strip():
        errors.append("MAC地址不能为空")
    return errors

def validate_mapping_form(model_id, standard_field_id, device_field_name):
    """验证映射表单"""
    errors = []
    if not model_id:
        errors.append("请选择设备型号")
    if not standard_field_id:
        errors.append("请选择标准字段")
    if not device_field_name.strip():
        errors.append("原始字段名不能为空")
    return errors