import os
from dotenv import load_dotenv, find_dotenv
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv(find_dotenv())   # 自动找到项目根的 .env
DATABASE_URL = os.getenv("DATABASE_URL") 

if not DATABASE_URL:
    raise RuntimeError(
        "Missing env var DATABASE_URL. Example:\n"
        "  export DATABASE_URL=postgresql+psycopg://rag_user:rag_password@localhost:5432/rag_db"
    )
    
engine = create_engine(DATABASE_URL, pool_pre_ping=True)    # 创建数据库引擎，启用连接池预检测
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # 创建会话工厂

@contextmanager
def get_db():
    """
    上下文管理器：with db_session() as db:
        ... 使用 db 执行业务 ...
    结束时自动提交或回滚，并关闭连接
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # 正常结束则提交事务
    except Exception:
        db.rollback()  # 出错则回滚事务
        raise
    finally:
        db.close()