"""后台处理文档向量化与进度上报。"""
from __future__ import annotations

import logging
import os
import threading
import time
from functools import lru_cache
from queue import Empty, Queue

from app.db.session import SessionLocal
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.document_repo import DocumentRepository
from app.services.rag_service import index_chunks

logger = logging.getLogger(__name__)

_DEFAULT_BATCH_SIZE = 32
_BATCH_SIZE_ENV_VAR = "DOCUMENT_INDEX_BATCH_SIZE"

_WORK_QUEUE: "Queue[tuple[int, int]]" = Queue()
_WORKER_LOCK = threading.Lock()
_WORKER_THREAD: threading.Thread | None = None
_MAX_RETRIES = 5
_RETRY_DELAY_SECONDS = 1.0
@lru_cache(maxsize=1)
def get_configured_batch_size() -> int:
    """返回环境变量配置的批大小，若配置非法则回退默认值。"""

    raw_value = os.getenv(_BATCH_SIZE_ENV_VAR)
    if raw_value is None:
        return _DEFAULT_BATCH_SIZE

    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            "invalid_document_index_batch_size value=%s fallback=%s",
            raw_value,
            _DEFAULT_BATCH_SIZE,
        )
        return _DEFAULT_BATCH_SIZE

    if parsed < 1:
        logger.warning(
            "document_index_batch_size_too_small value=%s fallback=%s",
            parsed,
            _DEFAULT_BATCH_SIZE,
        )
        return _DEFAULT_BATCH_SIZE

    logger.info("document_index_batch_size_configured value=%s", parsed)
    return parsed


def _resolve_batch_size(explicit: int | None) -> int:
    """结合环境变量与显式参数计算最终批大小。"""

    if explicit is None:
        return get_configured_batch_size()

    if explicit < 1:
        logger.warning(
            "document_index_batch_size_override_invalid value=%s fallback=%s",
            explicit,
            _DEFAULT_BATCH_SIZE,
        )
        return get_configured_batch_size()

    return explicit


def _ensure_worker_running() -> None:
    """确保文档索引工作线程已经启动。"""

    global _WORKER_THREAD
    with _WORKER_LOCK:
        if _WORKER_THREAD and _WORKER_THREAD.is_alive():
            return

        def _worker() -> None:
            while True:
                try:
                    document_id, attempt = _WORK_QUEUE.get(timeout=1)
                except Empty:
                    continue

                try:
                    success = process_document_indexing(document_id)
                    if not success and attempt + 1 < _MAX_RETRIES:
                        delay = _RETRY_DELAY_SECONDS * (attempt + 1)
                        logger.debug(
                            "requeue_index_job document_id=%s attempt=%s delay=%s",
                            document_id,
                            attempt + 1,
                            delay,
                        )
                        time.sleep(delay)
                        _WORK_QUEUE.put((document_id, attempt + 1))
                    elif not success:
                        logger.error(
                            "index_job_dropped document_id=%s attempts=%s",
                            document_id,
                            attempt + 1,
                        )
                except Exception:  # pragma: no cover - 防御式兜底
                    logger.exception(
                        "index_document_worker_uncaught_error document_id=%s",
                        document_id,
                    )
                finally:
                    _WORK_QUEUE.task_done()

        _WORKER_THREAD = threading.Thread(
            target=_worker,
            name="document-indexing-worker",
            daemon=True,
        )
        _WORKER_THREAD.start()


def enqueue_document_indexing(document_id: int) -> None:
    """将文档加入索引队列，供后台线程异步处理。"""

    logger.debug("enqueue_document_index document_id=%s", document_id)
    _ensure_worker_running()
    _WORK_QUEUE.put((document_id, 0))


def resume_pending_index_jobs() -> None:
    """在服务启动时恢复仍处于排队/处理中状态的文档。"""

    db = SessionLocal()
    try:
        repo = DocumentRepository(db)
        candidate_ids = repo.list_ids_by_index_status(
            statuses=["queued", "processing", "pending"]
        )
        if candidate_ids:
            logger.info(
                "resume_pending_index_jobs count=%s", len(candidate_ids)
            )
        for doc_id in candidate_ids:
            enqueue_document_indexing(doc_id)
    finally:
        db.close()


def process_document_indexing(
    document_id: int,
    *,
    batch_size: int | None = None,
) -> bool:
    """对文档的所有 chunk 进行向量化，并实时更新进度。

    返回 ``True`` 表示无需重试，``False`` 表示因暂时性原因建议重试。
    """

    effective_batch = _resolve_batch_size(batch_size)
    db = SessionLocal()
    try:
        doc_repo = DocumentRepository(db)
        chunk_repo = ChunkRepository(db)
        document = doc_repo.get(document_id)
        if not document:
            logger.warning("index_document_missing document_id=%s", document_id)
            # 文档可能仍在创建事务中，返回 False 让工作线程稍后重试。
            return False

        if document.vector_index_status == "cancelled":
            logger.info("index_document_skip_cancelled document_id=%s", document_id)
            return True

        if document.vector_index_status not in {"queued", "pending", "processing"}:
            logger.info(
                "index_document_skip_status document_id=%s status=%s",
                document_id,
                document.vector_index_status,
            )
            return True

        total = chunk_repo.count_by_document(document_id)
        document.vector_total_chunks = total
        document.vector_index_error = None
        if total == 0:
            document.vector_indexed_chunks = 0
            document.vector_index_status = "completed"
            db.commit()
            logger.info("index_document_skipped_empty document_id=%s", document_id)
            return True

        # 为重新入队的任务重置进度，保证显示一致性。
        document.vector_indexed_chunks = 0
        document.vector_index_status = "processing"
        db.commit()

        processed = 0
        offset = 0
        logger.info(
            "index_document_started document_id=%s total=%s batch_size=%s",
            document_id,
            total,
            effective_batch,
        )

        while True:
            batch = chunk_repo.list_by_document(
                document_id, limit=effective_batch, offset=offset
            )
            if not batch:
                break
            offset += len(batch)
            db.refresh(document, attribute_names=["vector_index_status"])
            if document.vector_index_status == "cancelled":
                logger.info(
                    "index_document_cancelled_midflight document_id=%s processed=%s total=%s",
                    document_id,
                    processed,
                    total,
                )
                return True
            try:
                indexed = index_chunks(batch)
            except RuntimeError as exc:
                document.vector_index_status = "failed"
                document.vector_index_error = str(exc)
                db.commit()
                logger.exception(
                    "index_document_failed document_id=%s processed=%s total=%s",
                    document_id,
                    processed,
                    total,
                )
                return True
            processed += indexed
            document.vector_indexed_chunks = processed
            document.vector_total_chunks = total
            document.vector_index_error = None
            db.commit()

        db.refresh(document, attribute_names=["vector_index_status"])
        if document.vector_index_status == "cancelled":
            logger.info(
                "index_document_cancelled_after_loop document_id=%s processed=%s total=%s",
                document_id,
                processed,
                total,
            )
            return True

        document.vector_index_status = "completed"
        document.vector_index_error = None
        document.vector_indexed_chunks = processed
        document.vector_total_chunks = total
        db.commit()
        logger.info(
            "index_document_completed document_id=%s total=%s", document_id, total
        )
        return True
    except Exception as exc:  # pragma: no cover - 防御式兜底
        logger.exception("index_document_unexpected_error document_id=%s", document_id)
        db.rollback()
        try:
            document = DocumentRepository(db).get(document_id)
            if document:
                document.vector_index_status = "failed"
                document.vector_index_error = str(exc)
                db.commit()
        except Exception:  # pragma: no cover - 二次失败直接放弃
            db.rollback()
        return True
    finally:
        db.close()
