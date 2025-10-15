from pydantic import BaseModel, ConfigDict

class ORMModel(BaseModel):
    """所有 Schema 的基类：开启 from_attributes 以支持 ORM 对象 -> 输出"""
    model_config = ConfigDict(from_attributes=True)
