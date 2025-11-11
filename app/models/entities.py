"""系统中的所有SQLAlchemy实体定义。"""  # 模块级注释，说明此处集中定义ORM模型
from __future__ import annotations  # 允许在类型注解中引用尚未定义的类，避免循环引用问题

import uuid  # 提供UUID生成功能用于文档与切片标识
from typing import List, Optional, ClassVar  # 引入类型注解以提升代码可读性

from sqlalchemy import (  # 导入SQLAlchemy核心字段类型与工具函数
    BigInteger,  # 使用大整型作为主键以兼容高增长数据量
    Boolean,  # 布尔型用于管理员标志
    CheckConstraint,  # 约束消息角色取值范围
    DateTime,  # 日期时间类型用于审计字段
    ForeignKey,  # 外键定义确保实体之间的引用一致
    Index,  # 显式索引定义提高查询性能
    Integer,  # 普通整型用于统计字段
    JSON,  # JSON字段存储文档元数据
    String,  # 可变长度字符串类型
    Text,  # 长文本类型存储消息与文档内容
    UniqueConstraint,  # 复合唯一约束保证业务唯一性
    func,  # SQL函数工具用于服务器默认值
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID  # 使用PostgreSQL专有UUID类型确保数据库端原生支持
from sqlalchemy.orm import Mapped, mapped_column, relationship  # SQLAlchemy2.0风格映射API

from .base import Base  # 所有模型继承自自定义的Base，提供统一表名策略


class User(Base):  # 定义用户实体，对应用户表
    """用户表，负责存储账号信息与权限。"""  # 类文档简述用途
    __tablename__: ClassVar[str] = "user"  # 显式指定表名与历史数据库保持一致

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # 主键自增，满足唯一标识需求
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)  # 邮箱作为登录名并加唯一约束防止重复注册
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)  # 存储哈希后的密码，绝不保存明文
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 可选的用户全名字段，用于展示
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")  # 管理员标志默认关闭以防权限滥用
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())  # 创建时间自动填充当前时刻
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())  # 更新时间在每次写入时刷新
    chats: Mapped[List["Chat"]] = relationship(  # 建立与聊天的关系以方便级联访问
        "Chat",  # 关联的目标模型
        back_populates="user",  # 与Chat.user字段互相指向
        cascade="all, delete-orphan",  # 删除用户时一并删除其聊天，避免孤儿记录
        passive_deletes=True,  # 配合数据库ON DELETE CASCADE减少额外SQL
    )  # 设计说明见下面的注释

    __table_args__ = (  # 定义额外的表级配置
        Index("ix_user_email", "email", unique=True),  # 为邮箱创建唯一索引，提升登录查询速度并保证唯一性
    )  # 表参数结束


class Chat(Base):  # 定义聊天会话实体
    """聊天会话表，记录用户开启的每个对话。"""  # 类文档说明职责
    __tablename__: ClassVar[str] = "chats"  # 对应数据库中的chats表

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # 聊天主键
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)  # 外键指向用户，删除用户时级联删除聊天保持一致性
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 聊天标题可为空，便于前端自定义
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())  # 创建时间自动填充
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())  # 更新时间自动更新
    user: Mapped["User"] = relationship("User", back_populates="chats", passive_deletes=True)  # 反向关系方便从聊天访问所属用户
    messages: Mapped[List["Message"]] = relationship(  # 建立聊天与消息的一对多关系
        "Message",  # 关联消息模型
        back_populates="chat",  # 与Message.chat互相引用
        cascade="all, delete-orphan",  # 删除聊天时级联删除消息，避免消息孤立
        passive_deletes=True,  # 交给数据库执行ON DELETE CASCADE减少显式删除
    )


class Message(Base):  # 定义消息实体
    """消息表，存储对话过程中的每条消息。"""  # 类文档说明用途
    __tablename__: ClassVar[str] = "messages"  # 对应数据库messages表

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # 消息主键
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)  # 外键指向聊天，聊天删除时级联删除消息
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # 消息角色限定为user/system/assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 消息正文内容
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())  # 创建时间自动填充
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())  # 更新时间自动刷新
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages", passive_deletes=True)  # 反向关系，便于从消息获取聊天

    __table_args__ = (  # 消息表级约束
        CheckConstraint("role IN ('user', 'system', 'assistant')", name="chk_message_role"),  # 限制角色取值范围防止脏数据
        Index("ix_messages_chat_id_created_at", "chat_id", "created_at"),  # 复合索引提升按时间查询性能
    )


class Domain(Base):  # 定义数据来源实体
    """Domain 表示知识来源，用于对文档分组。"""  # 类文档说明
    __tablename__: ClassVar[str] = "domains"  # 数据库表名

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # 主键
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)  # 名称唯一防止重复录入
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 可选描述信息
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())  # 创建时间
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())  # 更新时间
    documents: Mapped[List["Document"]] = relationship(  # 域与文档一对多关系
        "Document",  # 关联文档模型
        back_populates="domain",  # 反向引用
        cascade="all, delete-orphan",  # 删除domain时级联清理文档，保持数据一致
        passive_deletes=True,  # 启用数据库级联
    )


class Document(Base):  # 定义文档实体
    """Document 存储原始文档内容及元数据。"""  # 类文档说明
    __tablename__: ClassVar[str] = "documents"  # 对应数据库表

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # 文档主键
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)  # 外键指向domain，删除domain时级联
    uuid: Mapped[uuid.UUID] = mapped_column(  # 文档对外暴露的无序标识
        PGUUID(as_uuid=True),  # 使用PostgreSQL原生UUID类型
        nullable=False,  # 禁止空值确保每个文档均有标识
        default=uuid.uuid4,  # 默认生成uuid4避免可预测
        unique=True,  # 保证对外标识唯一
        index=True,  # 建索引方便按uuid查询
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)  # 文档标题
    doc_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # 元数据存储结构化信息
    raw_content: Mapped[str] = mapped_column(  # 存储文档原始内容，支持后续详情展示
        Text,
        nullable=False,
        default="",
    )
    vector_index_status: Mapped[str] = mapped_column(  # 记录向量索引状态
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    vector_indexed_chunks: Mapped[int] = mapped_column(  # 已成功写入向量库的chunk数量
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    vector_total_chunks: Mapped[int] = mapped_column(  # 需要索引的chunk总数
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    vector_index_error: Mapped[Optional[str]] = mapped_column(  # 最近一次索引失败的错误信息
        Text,
        nullable=True,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())  # 创建时间
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())  # 更新时间
    domain: Mapped["Domain"] = relationship("Domain", back_populates="documents", passive_deletes=True)  # 反向关系
    chunks: Mapped[List["Chunk"]] = relationship(  # 文档与切片一对多关系
        "Chunk",  # 关联模型
        back_populates="document",  # 反向指针
        cascade="all, delete-orphan",  # 文档删除时清理切片，保持一致
        passive_deletes=True,  # 交由数据库执行级联
    )

    __table_args__ = (  # 文档附加索引
        Index("ix_documents_domain_id_created_at", "domain_id", "created_at"),  # 提升按域和时间排序的查询效率
    )



class Chunk(Base):  # 定义文档切片实体
    """Chunk 表示拆分后的文档片段。"""  # 类文档说明
    __tablename__: ClassVar[str] = "chunks"  # 数据库表名

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # 主键
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)  # 外键指向文档并建立索引
    external_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))  # 对接外部存储的唯一标识
    ordinal: Mapped[int] = mapped_column(nullable=False, default=0)  # 在文档中的顺序位置
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 切片内容正文
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())  # 创建时间
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())  # 更新时间
    document: Mapped["Document"] = relationship("Document", back_populates="chunks", passive_deletes=True)  # 反向关系便于加载

    __table_args__ = (  # 附加约束
        UniqueConstraint("document_id", "ordinal", name="uq_chunk_doc_ordinal"),  # 同一文档内ordinal唯一，保证顺序稳定
        Index("ix_chunks_document_ordinal", "document_id", "ordinal"),  # 索引加速按顺序查询
    )
