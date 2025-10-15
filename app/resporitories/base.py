from typing import Generic, TypeVar, Type, Any, Sequence
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)

class Repository(Generic[ModelT]):
    """
    通用仓储基类：
    提供对单个实体类的CRUD操作。
    通过泛型参数ModelT指定具体的实体类类型。
    依赖注入SQLAlchemy的Session实例。
    通过传入的实体类类型，动态执行对应的数据库操作。
    """
    def __init__(self, db: Session, model: Type[ModelT]):
        self.db = db
        self.model = model

    # 读
    def get(self, id_: Any) -> ModelT | None:
        return self.db.get(self.model, id_)

    # 列表（可带 offset/limit）
    def list(self, offset: int = 0, limit: int = 50) -> Sequence[ModelT]:
        stmt = select(self.model).offset(offset).limit(limit)
        return self.db.execute(stmt).scalars().all()

    # 增
    def create(self, **data) -> ModelT:
        obj = self.model(**data)
        self.db.add(obj)
        self.db.flush()  # 立刻得到自增主键
        return obj

    # 改（部分字段）
    def update(self, obj: ModelT, **data) -> ModelT:
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        self.db.add(obj)
        self.db.flush()
        return obj

    # 删
    def delete(self, id_: Any) -> None:
        obj = self.get(id_)
        if obj is not None:
            self.db.delete(obj)
            self.db.flush()
