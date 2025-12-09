"""文档切分服务，负责生成chunk文本。"""
from __future__ import annotations  # 允许前置注解

import csv  # 解析结构化CSV内容
import io  # 提供内存文本缓冲
import json  # 解析结构化JSON内容
import logging  # 记录切分过程方便调试
import os  # 读取可配置的CSV字段长度限制
import re  # 通过正则匹配识别 URL
import sys  # 调整CSV字段长度限制
from typing import Any, Dict, List  # 类型注解辅助

from app.models.entities import Document  # 引入Document模型以读取元数据

logger = logging.getLogger(__name__)  # 初始化日志
CHUNK_SIZE = 400;

def chunk_text_sliding_window(text: str, size: int = 400, overlap: int = 50) -> List[str]:
    """使用滑动窗口算法切分长文本。
    额外保证：
    1) 若英文类单词在窗口起点被截断，下一个chunk回退起点以完整包含该单词（允许实际重叠 > overlap）。
    2) 若英文类单词在窗口终点被截断，则本chunk回退终点到该单词起点，让该单词完整出现在下一个chunk。
    """
    if not text:
        return []
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")

    step = size - overlap
    if step <= 0:
        raise ValueError("size must be greater than overlap")

    # 仅保护 ASCII 类“有空格分词习惯”的单词
    word_char_re = re.compile(r"[A-Za-z0-9_]")
    def _is_word_char(ch: str) -> bool:
        return bool(word_char_re.match(ch))

    def _adjust_start_to_word_boundary(value: str, proposed_start: int, prev_start: int) -> int:
        """若 proposed_start 落在单词内部，则回退到该单词起点。"""
        n = len(value)
        if proposed_start <= 0 or proposed_start >= n:
            return proposed_start

        if _is_word_char(value[proposed_start]) and _is_word_char(value[proposed_start - 1]):
            i = proposed_start
            while i > 0 and _is_word_char(value[i - 1]):
                i -= 1
            # 防止不前进
            if i <= prev_start:
                return proposed_start
            return i

        return proposed_start

    def _adjust_end_to_word_boundary(value: str, end: int, start: int) -> int:
        """若 end 落在单词内部，则回退到该单词起点，避免本chunk末尾出现半个单词。"""
        n = len(value)
        if end <= 0 or end >= n:
            return end

        # end-1 与 end 都是单词字符 => 边界切在词中
        if _is_word_char(value[end - 1]) and _is_word_char(value[end]):
            i = end
            while i > 0 and _is_word_char(value[i - 1]):
                i -= 1
            # 如果这个词太长导致回退到 start 甚至更前，则无法避免截断，保留原 end
            if i <= start:
                return end
            return i

        return end

    def _chunk_plain_text(value: str) -> List[str]:
        if not value:
            return []

        result: List[str] = []
        start = 0
        n = len(value)

        while start < n:
            raw_end = min(start + size, n)
            end = raw_end

            if end < n:
                end = _adjust_end_to_word_boundary(value, end, start)

                # 极端防护：若 end 被回退得过头导致空片段，回到 raw_end
                if end <= start:
                    end = raw_end

            result.append(value[start:end])

            if end == n:
                break

            # 关键变化：下一段起点基于 end 而不是固定 step
            proposed_start = max(0, end - overlap)
            next_start = _adjust_start_to_word_boundary(value, proposed_start, start)

            # 防死循环：如果仍未前进，退回原逻辑的 step 推进
            if next_start <= start:
                next_start = min(start + step, n)

            start = next_start

        return result

    url_pattern = re.compile(r"https?://[^\s<>\u3000\"']+", re.IGNORECASE)
    chunks: List[str] = []
    cursor = 0
    text_length = len(text)

    for match in url_pattern.finditer(text):
        url_start, url_end = match.span()
        line_start = text.rfind("\n", 0, url_start)
        line_start = 0 if line_start == -1 else line_start + 1

        prefix_start = url_start
        prefix_slice = text[line_start:url_start]
        label_match = re.search(r"档案请求地址：\s*$", prefix_slice)
        if label_match:
            prefix_start = line_start + label_match.start()

        chunks.extend(_chunk_plain_text(text[cursor:prefix_start]))

        url_chunk = text[prefix_start:url_end]
        if url_chunk:
            chunks.append(url_chunk)

        cursor = url_end

    chunks.extend(_chunk_plain_text(text[cursor:]))

    logger.info(
        "chunk_sliding_window length=%s size=%s overlap=%s count=%s",
        text_length,
        size,
        overlap,
        len(chunks),
    )
    return chunks


def _flatten_structured_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """将嵌套的结构化数据打平成以冒号分隔的键路径。"""

    flattened: Dict[str, Any] = {}

    def _walk(current_key: str, value: Any) -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                key_str = str(child_key).strip()
                if not key_str:
                    continue
                next_key = f"{current_key}:{key_str}" if current_key else key_str
                _walk(next_key, child_value)
            return
        if not current_key:
            return
        flattened[current_key] = value

    for key, value in data.items():
        key_str = str(key).strip()
        if not key_str:
            continue
        _walk(key_str, value)

    return flattened


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
    base_prefix = f"{entity_name}:{key}:" if entity_name else f"{key}:"
    prefix = base_prefix
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
    max_len: int = CHUNK_SIZE,
    overlap: int = 50,
) -> List[str]:
    """针对结构化实体列表生成紧凑描述字符串。"""
    def _build_prefix(entity_name: str, entity_data: Dict[str, Any]) -> str:
        """返回以实体名或首个字段内容为值的前缀，不计入长度限制。"""

        if entity_name:
            return ""  # 已有实体名开头，无需额外前缀

        for value in entity_data.values():
            if value is None:
                continue
            value_str = str(value).strip()
            if value_str:
                return f"{value_str}:"
        return ""

    chunks: List[str] = []  # 存放生成的文本段
    for entity in entities:
        name = str(entity.get("entity", "") or "").strip()  # 获取实体名称，允许为空
        data = _flatten_structured_data(entity.get("data") or {})  # 取出并打平属性字典
        if not isinstance(data, dict):
            data = {}  # 异常结构时回退为空字典
        prefix = _build_prefix(name, data)
        entity_chunks: List[str] = []
        current = name  # 初始化当前段落以实体名开头（可为空）
        first = True  # 标记是否为第一对键值
        for key, value in data.items():
            key_str = str(key)
            value_str = "" if value is None else str(value)
            pair = f"{key_str}:{value_str}"  # 组装键值描述
            pair_with_prefix = f"{name}:{pair}" if name else pair
            if len(value_str) > max_len or len(pair_with_prefix) > max_len:
                if current != name:
                    entity_chunks.append(current)
                split_chunks = _split_value_with_window(
                    name,
                    key_str,
                    value_str,
                    max_len,
                    overlap,
                )
                entity_chunks.extend(split_chunks)
                current = name
                first = True
                continue
            if name:
                separator = ":" if first else ","  # 第一对使用冒号其余使用逗号
                candidate = f"{current}{separator}{pair}"  # 预组装新段落
            else:
                separator = "" if first else ","  # 无实体名时首个键值无前缀
                candidate = f"{current}{separator}{pair}"
            if len(candidate) > max_len:
                if current != name:
                    entity_chunks.append(current)
                current = f"{name}:{pair}" if name else pair  # 超长时新开一段从当前键值开始
            else:
                current = candidate  # 未超长则继续累积
            first = False  # 之后的键值都走逗号
        if current and current != name:
            entity_chunks.append(current)  # 实体数据遍历完毕写入结果
        if prefix:
            chunks.extend([f"{prefix}{chunk}" for chunk in entity_chunks])
        else:
            chunks.extend(entity_chunks)
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
    """将CSV文本转成JSON格式，再复用JSON解析逻辑。"""

    if not csv_text:
        return []

    stream = io.StringIO(csv_text)
    try:
        try:
            csv.field_size_limit(MAX_CSV_FIELD_SIZE)
        except OverflowError:
            csv.field_size_limit(sys.maxsize)
        reader = csv.DictReader(stream)
    except csv.Error:
        return []

    rows = list(reader)
    if not rows:
        return []

    json_text = json.dumps(rows)
    return parse_structured_entities_from_json(json_text)


def parse_structured_entities_from_json(json_text: str) -> List[Dict[str, Any]]:
    """将JSON文本解析为实体列表，并展开嵌套字段。

    兼容多种结构：
    - {"entities": [...]} 或直接的数组
    - 单个对象（会按唯一条目处理）
    - 缺少 entity 字段时会尝试 name/title/id 等常见字段。
    """

    if not json_text:
        return []

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, dict) and isinstance(parsed.get("entities"), list):
        candidates = parsed["entities"]
    elif isinstance(parsed, list):
        candidates = parsed
    elif isinstance(parsed, dict):
        candidates = [parsed]
    else:
        return []

    entities: List[Dict[str, Any]] = []
    for index, item in enumerate(candidates):
        if not isinstance(item, dict):
            continue

        name_candidates = [
            item.get("entity"),
            item.get("name"),
            item.get("title"),
            item.get("id"),
        ]
        entity_name = ""
        for candidate in name_candidates:
            if candidate is None:
                continue
            candidate_str = str(candidate).strip()
            if candidate_str:
                entity_name = candidate_str
                break

        data = item.get("data")
        if not isinstance(data, dict):
            data = {key: value for key, value in item.items() if key != "entity"}
        flattened = _flatten_structured_data(data)
        if not flattened:
            continue
        entity_payload: Dict[str, Any] = {"data": flattened}
        if entity_name:
            entity_payload["entity"] = entity_name
        entities.append(entity_payload)

    return entities


def make_chunks(
    document: Document,
    content: str,
    size: int = CHUNK_SIZE,
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
        parsed_entities = parse_structured_entities_from_json(content) or None
    if parsed_entities and structured_type:
        logger.info("make_chunks structured uuid=%s", document.uuid)  # 记录采用结构化策略
        return chunk_structured_entities(parsed_entities)  # 优先使用结构化拆分
    if parsed_entities and not structured_type:
        logger.info("make_chunks structured_by_content uuid=%s", document.uuid)  # 内容提示结构化但未标记
        return chunk_structured_entities(parsed_entities)  # 内容具有结构仍采用结构化
    logger.info("make_chunks sliding uuid=%s", document.uuid)  # 默认使用滑动窗口
    return chunk_text_sliding_window(content, size=size, overlap=overlap)  # 回退滑窗
    # 设计说明：统一入口根据元数据与内容判断策略，保障后续扩展易于维护。
