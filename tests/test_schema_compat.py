"""Tests for legacy schema compatibility helpers."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    text,
)

from app.db.schema_compat import ensure_document_uuid_column


def _create_legacy_documents_table():
    """Return metadata containing a legacy ``documents`` table definition."""
    metadata = MetaData()
    Table(
        "documents",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("domain_id", Integer, nullable=False),
        Column("title", String(255), nullable=False),
        Column("doc_metadata", JSON, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    return metadata


def test_ensure_document_uuid_column_backfills_missing_column():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata = _create_legacy_documents_table()
    metadata.create_all(engine)

    documents = metadata.tables["documents"]
    with engine.begin() as conn:
        conn.execute(
            documents.insert(),
            {
                "domain_id": 1,
                "title": "Legacy Document",
                "doc_metadata": {},
                "created_at": dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc),
                "updated_at": dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc),
            },
        )

    # First call should patch the schema and backfill existing data.
    changed = ensure_document_uuid_column(engine)
    assert changed is True

    with engine.connect() as conn:
        inspector = inspect(conn)
        column_names = {col["name"] for col in inspector.get_columns("documents")}
        assert "uuid" in column_names

        index_names = {idx["name"] for idx in inspector.get_indexes("documents")}
        assert "ix_documents_uuid" in index_names

        uuid_value = conn.execute(text("SELECT uuid FROM documents")).scalar_one()
        assert uuid_value is not None

    # Second call should be a no-op and preserve previously generated values.
    changed_again = ensure_document_uuid_column(engine)
    assert changed_again is False

    with engine.connect() as conn:
        persisted_uuid = conn.execute(text("SELECT uuid FROM documents")).scalar_one()
        assert persisted_uuid == uuid_value
