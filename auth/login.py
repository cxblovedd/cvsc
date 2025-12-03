import streamlit as st
from config import config

def check_login(username, password):
    """验证用户登录"""
    return username in config.VALID_USERS and config.VALID_USERS[username] == password

def render_login_page():
    """渲染登录页面"""
    
    # 居中显示登录表单
    st.markdown("""
    <div style='display: flex; justify-content: center; align-items: center; height: 80vh;'>
        <div style='text-align: center; width: 400px; padding: 2rem; border: 1px solid #ddd; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);'>
            <h1>🏥 CVSC 中央体征管理平台</h1>
            <p style='color: #666; margin-bottom: 2rem;'>请登录以继续访问</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("用户名", placeholder="请输入用户名")
        password = st.text_input("密码", type="password", placeholder="请输入密码")
        submitted = st.form_submit_button("登录", use_container_width=True)
        
        if submitted:
            if username and password:
                if check_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success(f"欢迎回来，{username}！")
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
            else:
                st.error("请输入用户名和密码")

def check_authentication():
    """检查用户是否已登录"""
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        render_login_page()
        return False
    return True

def logout():
    """用户登出"""
    st.session_state.logged_in = False
    st.session_state.username = None
    if 'current_view' in st.session_state:
        del st.session_state.current_view
    if 'selected_patient_id' in st.session_state:
        del st.session_state.selected_patient_id