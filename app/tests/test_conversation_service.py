"""对话服务辅助函数的测试。"""
from __future__ import annotations

from types import SimpleNamespace

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import app.services.conversation_service as conversation_service
import app.services.rag_conversation as rag_conversation
from app.services import rag_service


def test_build_history_returns_ordered_messages():
    """历史消息应按创建时间顺序输出。"""

    class DummyRepo:
        def list_by_chat(self, chat_id: int, offset: int = 0, limit: int = 100):
            assert chat_id == 1
            return [
                SimpleNamespace(role="user", content="第一条"),
                SimpleNamespace(role="assistant", content="第二条"),
            ]

    history = conversation_service.build_history(1, db=None, message_repo=DummyRepo())
    assert history == [
        {"role": "user", "content": "第一条"},
        {"role": "assistant", "content": "第二条"},
    ]


def test_build_context_envelope_formats_chunks():
    """上下文包应包含摘要与格式化的证据片段。"""

    document = SimpleNamespace(title="档案 A")
    chunks = [
        SimpleNamespace(
            id=11,
            document_id=101,
            content="内容段落一" * 30,
            document=document,
        ),
    ]
    references = [(11, 0.876)]

    envelope = conversation_service.build_context_envelope("主题摘要", chunks, references)
    lines = envelope["content"].split("\n")
    assert lines[0] == "【上下文包】仅供参考，不是用户问题"
    assert lines[1] == "【滚动摘要】主题摘要"
    assert lines[2] == "【证据片段】"
    assert lines[3].startswith("[1] score=0.88 source=档案 A chunk_id=11")


def test_answer_with_history_composes_messages(monkeypatch):
    """编排后的消息序列应包含历史、上下文包与当前问题。"""

    history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "请问"},
        {"role": "user", "content": "现在的问题"},
    ]

    monkeypatch.setattr(rag_conversation, "build_history", lambda chat_id, db: history)

    def fake_generate(messages):
        assert messages == history
        return "滚动摘要"

    monkeypatch.setattr(rag_conversation, "generate_summary", fake_generate)

    envelope_message = {"role": "assistant", "content": "CTX"}

    def fake_context(summary, chunks, references):
        assert summary == "滚动摘要"
        assert len(references) == 2
        return envelope_message

    monkeypatch.setattr(rag_conversation, "build_context_envelope", fake_context)

    captured = {}

    def fake_retrieve(question, top_k, domain_ids, *, db):
        captured["top_k"] = top_k
        captured["domain_ids"] = domain_ids
        document = SimpleNamespace(title="档案 B")
        chunk1 = SimpleNamespace(id=21, document_id=201, content="内容1", document=document)
        chunk2 = SimpleNamespace(id=22, document_id=202, content="内容2", document=document)
        return [chunk1, chunk2], [(21, 0.9), (22, 0.8)]

    monkeypatch.setattr(rag_service, "retrieve_with_scores", fake_retrieve)

    sent = {}

    def fake_chat(system=None, user=None, *, messages=None, stream=False):
        sent["messages"] = messages
        return " 回答 "

    monkeypatch.setattr(rag_service, "chat", fake_chat)

    answer_text, references = rag_conversation.answer_with_history(
        chat_id=7,
        question="现在的问题",
        domain_ids=[1, 2],
        db=None,
        top_k=1,
    )

    assert captured["top_k"] == rag_service.EVIDENCE_TOP_K
    assert captured["domain_ids"] == [1, 2]

    msgs = sent["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[1] == history[0]
    assert msgs[2] == history[1]
    assert msgs[-2] == envelope_message
    assert msgs[-1] == history[-1]

    assert answer_text == "回答"
    assert references == [(21, 0.9)]
