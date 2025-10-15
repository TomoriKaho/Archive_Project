import uuid
from typing import List, Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index,
    JSON, String, Text, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class User(Base):
    """用户实体类，对应数据库中的user表。
    包含的字段有：
    - id: 用户的唯一标识符，主键，自增。
    - email: 用户的电子邮件地址，唯一且不能为空。
    - hashed_password: 用户的密码哈希值，不能为空。
    - is_admin: 布尔值，表示用户是否为管理员，默认为False，不能为空。
    - created_at: 记录用户创建时间，默认为当前时间。
    - updated_at: 记录用户信息最后更新时间，默认为当前时间，更新时自动修改为当前时间。
    - chats: 与用户相关的聊天记录，通过relationship属性与Chat实体类建立一对多关系。
    """
    __tablename__: str = "user"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False) # 存储哈希后的密码
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    chats: Mapped[List["Chat"]] = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    
class Chat(Base):
    """聊天实体类，对应数据库中的chats表。
    包含的字段有：
    - id: 聊天的唯一标识符，主键，自增。
    - user_id: 外键，关联到user表的id字段，不能为空。
    - title: 聊天的标题，可为空。
    - created_at: 记录聊天创建时间，默认为当前时间。
    - updated_at: 记录聊天最后更新时间，默认为当前时间，更新时自动修改为当前时间。
    - user: 与聊天相关的用户，通过relationship属性与User实体类建立多对一关系。
    - messages: 与聊天相关的消息记录，通过relationship属性与Message实体类建立一对多关系。
    """
    __tablename__: str = "chats"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    user: Mapped["User"] = relationship("User", back_populates="chats", passive_deletes=True)
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    
class Message(Base):
    """ 消息实体类，对应数据库中的messages表。
    包含的字段有：
    - id: 消息的唯一标识符，主键，自增。
    - chat_id: 外键，关联到chats表的id字段，不能为空。
    - role: 消息的角色（如用户、系统等），不能为空。
    - content: 消息的内容，不能为空。
    - created_at: 记录消息创建时间，默认为当前时间。
    - updated_at: 记录消息最后更新时间，默认为当前时间，更新时自动修改为当前时间。
    - chat: 与消息相关的聊天，通过relationship属性与Chat实体类建立多对一关系。
    - 复合唯一约束：确保同一聊天中的消息内容唯一。
    - 索引：在chat_id和created_at字段上创建索引以优化查询性能。
    """
    __tablename__: str = "messages"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages", passive_deletes=True)
    
    __table_args__ = (
        CheckConstraint("role IN ('user', 'system', 'assistant')", name="chk_message_role"),
        Index("ix_messages_chat_id_created_at", "chat_id", "created_at"),
    )   
    
class Domain(Base):
    """数据来源实体类，对应数据库中的domains表。
    包含的字段有：
    - id: 来源的唯一标识符，主键，自增。
    - name: 来源的名称，唯一且不能为空。
    - description: 来源的描述，可为空。
    - created_at: 记录来源创建时间，默认为当前时间。
    - updated_at: 记录来源最后更新时间，默认为当前时间，更新时自动修改为当前时间。
    - documents: 与来源相关的文档，通过relationship属性与Document实体类建立一对多关系。
    """
    __tablename__: str = "domains"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="domain", cascade="all, delete-orphan")
    
    
class Document(Base):
    __tablename__: str = "documents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    domain: Mapped["Domain"] = relationship("Domain", back_populates="documents", passive_deletes=True)
    chunks: Mapped[List["Chunk"]] = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")  
    __table_args__ = (
        Index("ix_documents_domain_id_created_at", "domain_id", "created_at"),
    )
    
class Chunk(Base):
    """文档块实体类，对应数据库中的chunks表。
    包含的字段有：
    - id: 文档块的唯一标识符，主键，自增。
    - document_id: 外键，关联到documents表的id字段，不能为空。
    - external_id: 文档块的外部唯一标识符，使用UUID生成，为向量库提供，库里只存(external_id, embedding)对，不能为空且唯一。
    - ordinal: 文档块在文档中的顺序，不能为空，默认为0。
    - content: 文档块的内容，不能为空。
    - created_at: 记录文档块创建时间，默认为当前时间。
    - updated_at: 记录文档块最后更新时间，默认为当前时间，更新时自动修改为当前时间。
    - document: 与文档块相关的文档，通过relationship属性与Document实体类建立多对一关系。
    - 复合唯一约束：确保同一文档中的ordinal唯一。
    - 索引：在document_id和ordinal字段上创建索引以优化查询性能。"""
    __tablename__: str = "chunks"   
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        default=lambda: str(uuid.uuid4()) 
    )
    ordinal: Mapped[int] = mapped_column(nullable=False, default=0)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())   

    document: Mapped["Document"] = relationship(back_populates="chunks", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="uq_chunk_doc_ordinal"),
        Index("ix_chunks_document_ordinal", "document_id", "ordinal"),
    )