"""Prompt assembly helpers for the RAG workflow."""
from __future__ import annotations

from typing import Sequence

from .types import RetrievedChunk


def build_context_text(chunks: Sequence[RetrievedChunk]) -> str:
    """Render retrieved chunks into a numbered context string."""

    lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        header = f"[{idx}] Document: {chunk.document_title} (chunk #{chunk.chunk_ordinal})"
        lines.append(header)
        lines.append(chunk.content.strip())
        lines.append("")
    return "\n".join(lines).strip()


def build_messages(question: str, chunks: Sequence[RetrievedChunk]) -> list[dict[str, str]]:
    """Create chat messages to send to Ollama."""

    if chunks:
        context_text = build_context_text(chunks)
    else:
        context_text = "(no relevant context was retrieved from the knowledge base)"
    system_prompt = (
        "You are a helpful assistant that answers questions using the supplied context. "
        "Always mention the supporting sources using [number] notation that corresponds "
        "to the provided context items. If the answer is not present in the context, "
        "respond that you do not know."
    )
    user_prompt = (
        "Context:\n"
        f"{context_text}\n\n"
        f"Question: {question}\n\n"
        "Provide a concise answer in Markdown and cite sources as [1], [2], etc."
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

