from sqlalchemy.orm import DeclarativeBase, declared_attr

class Base(DeclarativeBase):
    """所有模型的基类，自动生成表名为小写类名"""
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    