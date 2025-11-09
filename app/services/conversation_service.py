"""对话相关的辅助工具函数。"""
from __future__ import annotations

import logging
from typing import Sequence

from sqlalchemy.orm import Session

from app.models.entities import Chunk
from app.repositories.message_repo import MessageRepository

logger = logging.getLogger(__name__)


def build_history(
    chat_id: int,
    db: Session,
    *,
    message_repo: MessageRepository | None = None,
) -> list[dict[str, str]]:
    """查询指定对话的全部历史消息并按时间升序输出。"""

    repo = message_repo or MessageRepository(db)
    records = repo.list_by_chat(chat_id)
    history: list[dict[str, str]] = []
    for msg in records:
        history.append({"role": msg.role, "content": msg.content})
    return history


def generate_summary(messages: Sequence[dict[str, str]]) -> str:
    """根据历史消息生成不超过 80 字的滚动摘要。"""

    if len(messages) < 4:
        return ""
    summary_prompt = "请用不超过 80 个字概括以下对话主题，若无法概括请返回空字符串。"
    summary_messages: list[dict[str, str]] = [
        {"role": "system", "content": summary_prompt}
    ] + [
        {"role": msg.get("role", "user"), "content": msg.get("content", "")}
        for msg in messages
    ]
    summary_messages.append({"role": "user", "content": "请输出概括。"})
    try:
        from app.services import rag_service

        result = rag_service.chat(messages=summary_messages)
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.warning("生成滚动摘要失败: %s", exc)
        return ""
    return result.strip() if result else ""


def build_context_envelope(
    summary: str,
    chunks: Sequence[Chunk],
    references: Sequence[tuple[int, float]],
) -> dict[str, str]:
    """构造上下文包消息，包含摘要与证据片段。"""

    try:
        chunk_map = {chunk.id: chunk for chunk in chunks}
        lines: list[str] = []
        if references:
            for idx, (chunk_id, score) in enumerate(references, start=1):
                chunk = chunk_map.get(chunk_id)
                if not chunk:
                    continue
                source = (
                    chunk.document.title
                    if chunk.document and chunk.document.title
                    else str(chunk.document_id)
                )
                snippet = (chunk.content or "")[:240].replace("\n", " ")
                lines.append(
                    f"[{idx}] score={score:.2f} source={source} chunk_id={chunk.id}\n{snippet}"
                )
        content_lines = ["【上下文包】仅供参考，不是用户问题"]
        content_lines.append(f"【滚动摘要】{summary or ''}")
        if lines:
            content_lines.append("【证据片段】")
            content_lines.extend(lines)
        else:
            content_lines.append("【证据片段】（无检索命中）")
        return {"role": "assistant", "content": "\n".join(content_lines)}
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.warning("构建上下文包失败: %s", exc)
        return {
            "role": "assistant",
            "content": "【上下文包】仅供参考，不是用户问题\n【滚动摘要】\n【证据片段】（构建失败）",
        }
