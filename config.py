import os

class Config:
    """应用配置类"""
    
    # 数据库配置
    DB_USER = os.getenv('DB_USER', 'wnopuser')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'hayymoni2018')
    DB_HOST = os.getenv('DB_HOST', '10.52.197.73')
    DB_NAME = os.getenv('DB_NAME', 'UNIONDEV')
    
    @property
    def DB_CONNECTION_STR(self):
        return f"mssql+pyodbc://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}/{self.DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server"
    
    # Streamlit 配置
    PAGE_TITLE = "CVSC 中央体征管理平台"
    PAGE_LAYOUT = "wide"
    PAGE_ICON = "🏥"
    
    # 登录配置
    VALID_USERS = {
        "admin": "admin123",
        "doctor": "doctor123",
        "nurse": "nurse123"
    }
    
    # 缓存配置
    QUERY_CACHE_TTL = 600  # 10分钟
    FILTER_CACHE_TTL = 300  # 5分钟

# 全局配置实例
config = Config()