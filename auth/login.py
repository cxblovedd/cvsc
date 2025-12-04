import streamlit as st
from config import config

def check_login(username, password):
    """验证用户登录"""
    return username in config.VALID_USERS and config.VALID_USERS[username] == password

def get_user_role(username):
    """获取用户角色"""
    user_roles = {
        "admin": "admin",
        "doctor": "medical_staff", 
        "nurse": "medical_staff",
        "technician": "technical_staff"
    }
    return user_roles.get(username, "guest")

def get_user_permissions(role):
    """获取用户权限"""
    permissions = {
        "admin": ["dashboard", "search", "device_management", "field_mapping", "system_logs"],
        "medical_staff": ["dashboard", "search"],
        "technical_staff": ["device_management", "field_mapping", "system_logs"],
        "guest": []
    }
    return permissions.get(role, [])

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
                    
                    # 立即设置用户角色和权限
                    role = get_user_role(username)
                    st.session_state.user_role = role
                    st.session_state.user_permissions = get_user_permissions(role)
                    
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
    
    # 确保用户角色和权限已设置
    username = st.session_state.get('username')
    if username and 'user_role' not in st.session_state:
        role = get_user_role(username)
        st.session_state.user_role = role
        st.session_state.user_permissions = get_user_permissions(role)
        
        # 调试信息
        print(f"用户 {username} 角色: {role}, 权限: {st.session_state.user_permissions}")
    
    return True

def has_permission(permission):
    """检查用户是否有特定权限"""
    return permission in st.session_state.get('user_permissions', [])

def logout():
    """用户登出"""
    # 清理所有session状态
    keys_to_clear = [
        'logged_in', 'username', 'user_role', 'user_permissions',
        'current_view', 'selected_patient_id', 'search_step', 'search_filters'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]