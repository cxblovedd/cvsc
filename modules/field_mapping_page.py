import streamlit as st
from database.queries import get_field_mappings, add_field_mapping, get_device_models, get_standard_fields
from utils.helpers import validate_mapping_form
from components.common import render_footer

def render_field_mapping():
    """渲染字段映射页面"""
    st.title("🔌 协议字段映射配置")
    st.info("用于配置不同品牌监护仪原始数据与标准字段的对应关系")
    
    col_l, col_r = st.columns([2, 1])
    with col_l:
        mapping_df = get_field_mappings()
        st.dataframe(mapping_df, use_container_width=True, hide_index=True)
    
    with col_r:
        st.subheader("新增映射")
        models = get_device_models()
        standards = get_standard_fields()
        
        with st.form("add_map"):
            model_names = models['id'].tolist() if not models.empty else []
            standard_names = standards['id'].tolist() if not standards.empty else []
            
            mid = st.selectbox(
                "设备型号", 
                model_names,
                format_func=lambda x: models[models['id']==x]['model_name'].values[0] if not models.empty else ""
            )
            sid = st.selectbox(
                "标准字段", 
                standard_names,
                format_func=lambda x: standards[standards['id']==x]['description'].values[0] if not standards.empty else ""
            )
            fname = st.text_input("原始字段名 (Key)")
            formula = st.text_input("转换公式 (默认 x*1)", value="x*1.0")
            
            if st.form_submit_button("保存"):
                errors = validate_mapping_form(mid, sid, fname)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    if add_field_mapping(mid, sid, fname, formula):
                        st.success("映射已保存")
                        st.rerun()
    
    render_footer()