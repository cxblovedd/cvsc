import streamlit as st
from database.queries import get_device_list, add_device, get_device_models, get_standard_fields
from utils.helpers import validate_device_form
from components.common import render_footer

def render_device_management():
    """渲染设备管理页面"""
    st.title("⚙️ 设备资产管理")
    
    tab1, tab2 = st.tabs(["📋 设备库存列表", "➕ 新增设备登记"])
    
    with tab1:
        df_devices = get_device_list()
        
        if not df_devices.empty:
            st.data_editor(
                df_devices,
                column_config={
                    "monitor_code": "设备编号",
                    "monitor_name": "名称",
                    "monitor_status": st.column_config.SelectboxColumn("在线状态", options=["在线", "离线"]),
                    "use_status": st.column_config.SelectboxColumn("使用状态", options=["使用中", "空闲"]),
                    "update_time": st.column_config.DatetimeColumn("更新时间", disabled=True)
                },
                use_container_width=True,
                hide_index=True
            )
            st.caption("注：直接编辑表格功能需对接后端 Update 接口")
    
    with tab2:
        with st.form("add_device"):
            c1, c2 = st.columns(2)
            code = c1.text_input("设备编号 (SN)")
            name = c2.text_input("设备名称/型号")
            mac = c1.text_input("MAC 地址")
            status = c2.selectbox("初始状态", ["空闲", "维护中"])
            
            if st.form_submit_button("提交入库"):
                errors = validate_device_form(code, name, mac)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    if add_device(code, name, mac, status):
                        st.success("添加成功")
                        st.rerun()
    
    render_footer()