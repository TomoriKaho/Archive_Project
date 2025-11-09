"""Schema compatibility helpers for legacy deployments.

These utilities detect older database schemas that predate recent
migrations and patch them in-place so that the application can continue to
operate without manual intervention.
"""
from __future__ import annotations

import logging
import uuid
from typing import Iterable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _table_exists(inspector, table_name: str) -> bool:
    """Return True if the given table exists in the connected database."""
    try:
        return table_name in inspector.get_table_names()
    except Exception:  # pragma: no cover - defensive fallback
        # Some dialects may fail when enumerating tables (e.g. lacking
        # privileges). In that case we optimistically assume the table
        # exists so that the caller can attempt to operate on it and raise a
        # more informative error.
        return True


def _get_column_names(inspector, table_name: str) -> set[str]:
    """Fetch the column names for the given table."""
    columns: Iterable[dict[str, object]] = inspector.get_columns(table_name)
    return {str(col["name"]) for col in columns}


def ensure_document_uuid_column(engine: Engine) -> bool:
    """Ensure ``documents.uuid`` exists and is populated.

    Older database snapshots lacked the ``uuid`` column that newer code relies
    on.  When the column is missing, domain deletion and any document queries
    fail with ``psycopg.errors.UndefinedColumn``.  This helper upgrades such
    installations in place by:

    1. Adding the ``uuid`` column.
    2. Backfilling existing rows with freshly generated UUID4 values.
    3. Marking the column ``NOT NULL`` when the dialect supports it.
    4. Creating the unique index used by the ORM mappings.

    The function returns ``True`` when a fix was applied and ``False`` when the
    schema was already up-to-date.  It is safe to call multiple times.
    """
    with engine.begin() as connection:
        inspector = inspect(connection)

        if not _table_exists(inspector, "documents"):
            logger.debug("documents table does not exist; skipping uuid check")
            return False

        column_names = _get_column_names(inspector, "documents")
        if "uuid" in column_names:
            logger.debug("documents.uuid already present; no action required")
            return False

        logger.warning(
            "Detected legacy documents table without uuid column; applying in-place upgrade."
        )

        # 1. Add the nullable UUID column so we can backfill values.
        connection.execute(text("ALTER TABLE documents ADD COLUMN uuid UUID"))

        # 2. Backfill every existing row with a stable UUID4 value.
        rows = connection.execute(text("SELECT id FROM documents"))
        for row in rows:
            document_id = row._mapping["id"]
            connection.execute(
                text("UPDATE documents SET uuid = :uuid WHERE id = :id"),
                {"uuid": str(uuid.uuid4()), "id": document_id},
            )

        # 3. Tighten the constraint when the backend supports ALTER COLUMN.
        if connection.dialect.name != "sqlite":
            connection.execute(
                text("ALTER TABLE documents ALTER COLUMN uuid SET NOT NULL")
            )

        # 4. Ensure the unique index exists for fast lookup by uuid.
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_uuid ON documents (uuid)"
            )
        )

        logger.info("documents.uuid column successfully backfilled")
        return True


def ensure_chat_domain_ids_column(engine: Engine) -> bool:
    """Ensure ``chats.domain_ids`` exists for legacy databases.

    Earlier deployments persisted conversations without the optional
    ``domain_ids`` JSON column that the refreshed chat experience depends on.
    When the ORM loads chats from such databases SQLAlchemy emits queries that
    reference the missing column, causing the entire chat view to fail with a
    ``psycopg.errors.UndefinedColumn`` error.  Similar to
    :func:`ensure_document_uuid_column`, we defensively patch the schema at
    runtime so instances continue to operate even if migrations were not
    executed yet.

    The function returns ``True`` when a fix was applied and ``False`` when the
    schema was already up-to-date.
    """

    with engine.begin() as connection:
        inspector = inspect(connection)

        if not _table_exists(inspector, "chats"):
            logger.debug("chats table does not exist; skipping domain_ids check")
            return False

        column_names = _get_column_names(inspector, "chats")
        if "domain_ids" in column_names:
            logger.debug("chats.domain_ids already present; no action required")
            return False

        logger.warning(
            "Detected legacy chats table without domain_ids column; applying in-place upgrade."
        )

        column_type = "JSON" if connection.dialect.name != "sqlite" else "TEXT"
        connection.execute(
            text(f"ALTER TABLE chats ADD COLUMN domain_ids {column_type}")
        )

        logger.info("chats.domain_ids column successfully added")
        return True
