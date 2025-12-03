import streamlit as st
import logging
from sqlalchemy import create_engine, text, exc
from config import config

logger = logging.getLogger(__name__)

@st.cache_resource
def get_db_engine():
    """创建数据库连接引擎"""
    try:
        engine = create_engine(
            config.DB_CONNECTION_STR,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False
        )
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ 数据库连接成功")
        return engine
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        raise

def test_connection():
    """测试数据库连接"""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
        return result[0] == 1
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False