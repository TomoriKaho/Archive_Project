"""文档切分服务，负责生成chunk文本。"""
from __future__ import annotations  # 允许前置注解

import csv  # 解析结构化CSV内容
import io  # 提供内存文本缓冲
import json  # 解析结构化JSON内容
import logging  # 记录切分过程方便调试
import os  # 读取可配置的CSV字段长度限制
import sys  # 调整CSV字段长度限制
from typing import Any, Dict, List  # 类型注解辅助

from app.models.entities import Document  # 引入Document模型以读取元数据

logger = logging.getLogger(__name__)  # 初始化日志


def chunk_text_sliding_window(text: str, size: int = 250, overlap: int = 50) -> List[str]:
    """使用滑动窗口算法切分长文本。"""
    if not text:
        return []  # 空文本直接返回空列表
    if size <= 0:
        raise ValueError("size must be positive")  # 防御性编程避免非法参数
    if overlap < 0:
        raise ValueError("overlap must be non-negative")  # 避免负数重叠
    step = size - overlap  # 计算每次移动步长
    if step <= 0:
        raise ValueError("size must be greater than overlap")  # 避免无限循环
    chunks: List[str] = []  # 初始化结果容器
    start = 0  # 当前窗口起始位置
    text_length = len(text)  # 使用字符长度而非字节，适配多语言
    while start < text_length:
        end = min(start + size, text_length)  # 计算窗口结束位置
        chunks.append(text[start:end])  # 切片并加入结果
        if end == text_length:
            break  # 到达末尾时终止循环
        start += step  # 按步长前进
    logger.info(
        "chunk_sliding_window length=%s size=%s overlap=%s count=%s",
        text_length,
        size,
        overlap,
        len(chunks),
    )  # 记录切分统计
    return chunks  # 返回所有窗口
    # 设计说明：滑动窗口保证相邻chunk存在overlap字符重叠，利于上层召回上下文。


def _split_value_with_window(
    entity_name: str,
    key: str,
    value: Any,
    max_len: int,
    overlap: int,
) -> List[str]:
    """Split a single key/value pair using a sliding window over the value text."""

    value_str = "" if value is None else str(value)
    # 尽量保留实体名称，若前缀过长则逐级降级，保证至少保留键名
    prefix = f"{entity_name}:{key}:"
    if len(prefix) >= max_len:
        prefix = f"{key}:"
        if len(prefix) >= max_len:
            trimmed_key = key[: max(0, max_len - 1)]
            prefix = f"{trimmed_key}:"
            if len(prefix) >= max_len:
                return [prefix] if prefix else []

    size = max(1, max_len)
    effective_overlap = 0 if size == 1 else min(overlap, size - 1)
    segments = chunk_text_sliding_window(value_str, size=size, overlap=effective_overlap)
    if not segments:
        return [prefix]
    return [f"{prefix}{segment}" for segment in segments]


def chunk_structured_entities(
    entities: List[Dict[str, Any]],
    max_len: int = 250,
    overlap: int = 50,
) -> List[str]:
    """针对结构化实体列表生成紧凑描述字符串。"""
    chunks: List[str] = []  # 存放生成的文本段
    for entity in entities:
        name = str(entity.get("entity", "Entity"))  # 获取实体名称缺省为Entity
        data = entity.get("data") or {}  # 取出属性字典
        if not isinstance(data, dict):
            data = {}  # 异常结构时回退为空字典
        current = name  # 初始化当前段落以实体名开头
        first = True  # 标记是否为第一对键值
        for key, value in data.items():
            key_str = str(key)
            value_str = "" if value is None else str(value)
            pair = f"{key_str}:{value_str}"  # 组装键值描述
            pair_with_prefix = f"{name}:{pair}"
            if len(value_str) > max_len or len(pair_with_prefix) > max_len:
                if current != name:
                    chunks.append(current)
                split_chunks = _split_value_with_window(
                    name,
                    key_str,
                    value_str,
                    max_len,
                    overlap,
                )
                chunks.extend(split_chunks)
                current = name
                first = True
                continue
            separator = ":" if first else ","  # 第一对使用冒号其余使用逗号
            candidate = f"{current}{separator}{pair}"  # 预组装新段落
            if len(candidate) > max_len:
                if current != name:
                    chunks.append(current)
                current = f"{name}:{pair}"  # 超长时新开一段从当前键值开始
            else:
                current = candidate  # 未超长则继续累积
            first = False  # 之后的键值都走逗号
        if current != name:
            chunks.append(current)  # 实体数据遍历完毕写入结果
    logger.info("chunk_structured_entities count=%s", len(chunks))  # 记录生成数量
    return chunks  # 返回所有结构化段落
    # 设计说明：利用len()按字符计算长度，比字节更符合前端展示长度且兼容中文字符宽度。


DEFAULT_MAX_CSV_FIELD_SIZE = 10 * 1024 * 1024  # 允许单字段最大10MB
MAX_CSV_FIELD_SIZE_ENV = "CSV_FIELD_SIZE_LIMIT"


def _resolve_max_csv_field_size() -> int:
    """从环境变量读取CSV字段长度限制，默认为10MB。"""

    raw_value = os.getenv(MAX_CSV_FIELD_SIZE_ENV)
    if not raw_value:
        return DEFAULT_MAX_CSV_FIELD_SIZE
    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid %s value %s, falling back to default %s",
            MAX_CSV_FIELD_SIZE_ENV,
            raw_value,
            DEFAULT_MAX_CSV_FIELD_SIZE,
        )
        return DEFAULT_MAX_CSV_FIELD_SIZE
    if parsed <= 0:
        logger.warning(
            "%s must be positive, falling back to default %s",
            MAX_CSV_FIELD_SIZE_ENV,
            DEFAULT_MAX_CSV_FIELD_SIZE,
        )
        return DEFAULT_MAX_CSV_FIELD_SIZE
    return parsed


MAX_CSV_FIELD_SIZE = _resolve_max_csv_field_size()


def parse_structured_entities_from_csv(csv_text: str) -> List[Dict[str, Any]]:
    """将CSV文本解析为实体列表，每个实体包含键值对数据。"""
    if not csv_text:
        return []  # 空文本直接返回
    stream = io.StringIO(csv_text)
    try:
        try:
            csv.field_size_limit(MAX_CSV_FIELD_SIZE)
        except OverflowError:
            csv.field_size_limit(sys.maxsize)
        reader = csv.DictReader(stream)
    except csv.Error:
        return []  # CSV格式错误直接返回空列表让上层决定
    if not reader.fieldnames:
        return []  # 无表头无法识别字段
    normalized_headers = [
        (header or "").strip() for header in reader.fieldnames
    ]  # 去除首尾空白
    entity_index = 0
    for idx, header in enumerate(normalized_headers):
        if header.lower() == "entity":
            entity_index = idx
            break
    entity_header = reader.fieldnames[entity_index]
    data_headers = [
        reader.fieldnames[idx]
        for idx in range(len(reader.fieldnames))
        if idx != entity_index and reader.fieldnames[idx] is not None
    ]
    aggregated: Dict[str, Dict[str, Any]] = {}
    for row in reader:
        entity_raw = row.get(entity_header)
        if entity_raw is None:
            continue
        entity = str(entity_raw).strip()
        if not entity:
            continue  # 跳过缺少实体名的行
        entity_data = aggregated.setdefault(entity, {})
        for header in data_headers:
            key_name = (header or "").strip()
            if not key_name:
                continue
            value = row.get(header)
            if value is None:
                continue
            value_str = str(value).strip()
            if not value_str:
                continue
            entity_data[key_name] = value_str
    return [
        {"entity": entity, "data": data}
        for entity, data in aggregated.items()
        if data
    ]


def make_chunks(
    document: Document,
    content: str,
    size: int = 250,
    overlap: int = 50,
    structured_entities: List[Dict[str, Any]] | None = None,
) -> List[str]:
    """根据文档元数据选择合适的切分策略。"""
    metadata: Dict[str, Any] = document.doc_metadata or {}  # 读取文档元数据
    if structured_entities:
        logger.info("make_chunks structured_preparsed uuid=%s", document.uuid)
        return chunk_structured_entities(structured_entities)
    structured_type = metadata.get("type") == "structured"  # 判断是否标记为结构化
    parsed_entities: List[Dict[str, Any]] | None = None  # 初始化解析结果
    if content:
        try:
            parsed = json.loads(content)  # 尝试解析JSON文本
            if isinstance(parsed, dict) and isinstance(parsed.get("entities"), list):
                parsed_entities = parsed["entities"]  # 提取实体列表
        except json.JSONDecodeError:
            logger.info("make_chunks json_decode_failed uuid=%s", document.uuid)  # 记录解析失败
    if parsed_entities and structured_type:
        logger.info("make_chunks structured uuid=%s", document.uuid)  # 记录采用结构化策略
        return chunk_structured_entities(parsed_entities)  # 优先使用结构化拆分
    if parsed_entities and not structured_type:
        logger.info("make_chunks structured_by_content uuid=%s", document.uuid)  # 内容提示结构化但未标记
        return chunk_structured_entities(parsed_entities)  # 内容具有结构仍采用结构化
    logger.info("make_chunks sliding uuid=%s", document.uuid)  # 默认使用滑动窗口
    return chunk_text_sliding_window(content, size=size, overlap=overlap)  # 回退滑窗
    # 设计说明：统一入口根据元数据与内容判断策略，保障后续扩展易于维护。
