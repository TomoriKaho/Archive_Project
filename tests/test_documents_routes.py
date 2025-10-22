"""文档路由辅助函数的单元测试。"""
import sys  # 修改sys.path以导入应用包
from dataclasses import dataclass, field  # 使用dataclass构造简单对象
from datetime import datetime  # 生成时间戳
from pathlib import Path  # 定位工程根目录
import uuid  # 生成uuid以模拟文档标识

sys.path.append(str(Path(__file__).resolve().parents[1]))  # 将项目根目录加入模块搜索路径

from app.api.documents import (  # 导入待测路由函数
    list_chunks,
    list_chunks_by_document_id,
    list_chunks_by_document_uuid,
)
from app.repositories.chunk_repo import ChunkRepository  # 仓储类用于monkeypatch
from app.repositories.document_repo import DocumentRepository
from app.repositories.domain_repo import DomainRepository
from app.schemas.chunk import ChunkOut  # 用于序列化比较


@dataclass
class FakeDocument:
    """模拟文档对象，仅保留测试所需字段。"""
    id: int
    domain_id: int
    uuid: uuid.UUID
    title: str = "Doc"
    doc_metadata: dict = field(default_factory=dict)


@dataclass
class FakeChunk:
    """模拟chunk对象，满足序列化所需字段。"""
    id: int
    document_id: int
    external_id: str
    ordinal: int
    content: str
    created_at: datetime
    updated_at: datetime


def test_chunk_routes_return_identical_payload(monkeypatch):
    """验证三条chunk路由的返回数据完全一致。"""
    doc_uuid = uuid.uuid4()  # 构造随机uuid
    fake_doc = FakeDocument(id=10, domain_id=1, uuid=doc_uuid)  # 构造文档对象
    now = datetime.utcnow()  # 当前时间用于填充时间字段
    fake_chunks = [
        FakeChunk(1, 10, "ext-1", 0, "chunk-1", now, now),
        FakeChunk(2, 10, "ext-2", 1, "chunk-2", now, now),
    ]  # 准备两个chunk

    monkeypatch.setattr(DomainRepository, "get", lambda self, _: object())  # domain存在校验
    monkeypatch.setattr(DocumentRepository, "get", lambda self, doc_id: fake_doc if doc_id == 10 else None)  # 按ID取文档
    monkeypatch.setattr(DocumentRepository, "get_by_uuid", lambda self, val: fake_doc if val == doc_uuid else None)  # 按UUID取文档
    monkeypatch.setattr(ChunkRepository, "list_by_document", lambda self, _: fake_chunks)  # 返回预置chunk

    def to_json(data):
        """辅助函数，将chunk对象序列化为dict。"""
        return [ChunkOut.model_validate(item).model_dump() for item in data]

    by_domain = to_json(list_chunks(fake_doc.domain_id, fake_doc.id, db=None))
    by_id = to_json(list_chunks_by_document_id(fake_doc.id, db=None))
    by_uuid = to_json(list_chunks_by_document_uuid(doc_uuid, db=None))

    assert by_domain == by_id == by_uuid  # 三个结果完全一致
    # 设计说明：通过对比JSON确保多路由共享统一服务逻辑。
