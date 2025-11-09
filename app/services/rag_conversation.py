"""基于历史消息的 RAG 对话编排。"""
from __future__ import annotations

import logging
from typing import Sequence

from sqlalchemy.orm import Session

from app.services import rag_service
from app.services.conversation_service import (
    build_context_envelope,
    build_history,
    generate_summary,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = "你是一名严谨的档案解读助手，只依据给定资料回答问题。"


def answer_with_history(
    chat_id: int,
    question: str,
    domain_ids: Sequence[int] | None,
    *,
    db: Session,
    top_k: int | None = None,
) -> tuple[str, list[tuple[int, float]]]:
    """执行带历史的 RAG 流程，并返回回答与参考证据。"""

    history = build_history(chat_id, db)
    if history and history[-1].get("role") == "user":
        current_user_message = history[-1]
        previous_messages = history[:-1]
    else:
        current_user_message = {"role": "user", "content": question}
        previous_messages = history

    summary = generate_summary(history)

    chunks, references = rag_service.retrieve_with_scores(
        question,
        rag_service.EVIDENCE_TOP_K,
        list(domain_ids) if domain_ids is not None else None,
        db=db,
    )

    envelope_message = build_context_envelope(summary, chunks, references)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_PROMPT}
    ] + previous_messages + [envelope_message, current_user_message]

    try:
        answer_text = rag_service.chat(messages=messages)
    except Exception as exc:
        logger.exception("调用聊天模型失败: chat_id=%s", chat_id)
        raise

    final_text = answer_text.strip() if answer_text else ""
    if not final_text:
        final_text = rag_service._NO_CONTEXT_MESSAGE

    limit = top_k or rag_service.DEFAULT_TOP_K
    limited_references = list(references)[:limit]
    return final_text, limited_references
