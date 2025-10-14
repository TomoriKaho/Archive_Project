from app.db.session import engine
from app.models.base import Base
from app.models import entities

if __name__ == "__main__":
    """ 创建数据库表, 如果表已存在则不会重复创建 """
    Base.metadata.create_all(bind=engine)  # 创建所有表
    print("Database tables created.")