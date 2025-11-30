"""Shared constants for Retrieval-Augmented Generation services."""

CHUNK_MEMORY_PREFIX = "__chunk_memory__:"
"""Marker used to persist retrieved chunk memory in ``Message.content``."""

CHAT_SUMMARY_PREFIX = "__chat_summary__:"
"""Marker used to persist compressed dialogue summaries per chat."""
