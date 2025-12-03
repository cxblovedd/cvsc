import streamlit as st
from database.queries import search_patients, get_filter_options
from components.patient_detail import render_patient_detail
from components.common import render_footer

def render_dashboard():
    """渲染实时监控看板页面"""
    st.title("📊 全院体征实时监控")
    
    # 状态管理：用于处理从列表点击查看详情的跳转
    if 'current_view' not in st.session_state:
        st.session_state.current_view = 'list'  # list or detail
    if 'selected_patient_id' not in st.session_state:
        st.session_state.selected_patient_id = None

    # 如果在详情页，显示返回按钮
    if st.session_state.current_view == 'detail':
        if st.button("⬅️ 返回患者列表"):
            st.session_state.current_view = 'list'
            st.session_state.selected_patient_id = None
            st.rerun()
        
        if st.session_state.selected_patient_id:
            render_patient_detail(st.session_state.selected_patient_id)
    else:
        # --- 列表/搜索视图 ---
        
        # 1. 顶部筛选区
        filter_opts = get_filter_options()
        
        with st.expander("🔍 患者检索与筛选条件", expanded=True):
            with st.form("search_form"):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    sel_location = st.selectbox("🏥 病区/科室", ["全部"] + filter_opts['locations'])
                with c2:
                    sel_type = st.selectbox("📋 就诊类型", ["全部"] + filter_opts['types'])
                with c3:
                    inp_bed = st.text_input("🛏️ 床号", placeholder="例如: 15")
                with c4:
                    inp_keyword = st.text_input("👤 姓名/ID", placeholder="姓名或住院号")
                
                c_submit, c_space = st.columns([1, 6])
                with c_submit:
                    submitted = st.form_submit_button("开始查询", use_container_width=True)

        # 2. 查询数据
        df_patients = search_patients(
            name=inp_keyword if inp_keyword else None,
            pid=inp_keyword if inp_keyword else None,
            bed_no=inp_bed,
            location=sel_location,
            p_type=sel_type
        )
        
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