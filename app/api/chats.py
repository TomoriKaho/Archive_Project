import logging
from types import SimpleNamespace

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.session import SessionLocal
from app.models.entities import User
from app.repositories.chat_repo import ChatRepository
from app.repositories.message_repo import MessageRepository
from app.schemas.chat import ChatCreate, ChatOut, ChatUpdate
from app.schemas.message import (
    MessageCreate,
    MessageCreateResponse,
    MessageOut,
    MessageReference,
    MessageUpdate,
)
from app.services.rag_constants import CHUNK_MEMORY_PREFIX, CHAT_SUMMARY_PREFIX
from app.services.rag_service import (
    CHUNK_MEMORY_WINDOW_MULTIPLIER,
    DEFAULT_TOP_K,
    answer,
    chunk_to_memory_text,
    compress_chunk_memory,
    compress_dialog_history,
    normalize_language_code,
)

logger = logging.getLogger(__name__)


def _run_post_answer_tasks(
    *,
    chat_id: int,
    question: str,
    answer_text: str,
    history_payload: list[dict[str, str]],
    chunk_texts: list[str],
    top_k: int,
) -> None:
    db = SessionLocal()
    try:
        repo = MessageRepository(db)
        memory_messages = repo.list_memory(chat_id)

        if chunk_texts:
            pseudo_chunks = [SimpleNamespace(content=text) for text in chunk_texts if text]
            compressed_memory = compress_chunk_memory(question, pseudo_chunks)
            if not compressed_memory:
                compressed_memory = "\n\n".join(text for text in chunk_texts if text)
            if compressed_memory:
                stored = repo.create(
                    chat_id=chat_id,
                    role="system",
                    content=f"{CHUNK_MEMORY_PREFIX}{compressed_memory}",
                )
                persisted_memory = list(memory_messages)
                persisted_memory.append(stored)
                window = (
                    CHUNK_MEMORY_WINDOW_MULTIPLIER * top_k
                    if CHUNK_MEMORY_WINDOW_MULTIPLIER > 0
                    else 0
                )
                if window and len(persisted_memory) > window:
                    overflow = len(persisted_memory) - window
                    to_delete = [m.id for m in persisted_memory[:overflow]]
                    repo.delete_many(to_delete)

        history_summary = compress_dialog_history(
            history_payload
            + [{"role": "user", "content": question}, {"role": "assistant", "content": answer_text}]
        )
        if history_summary:
            repo.create(
                chat_id=chat_id,
                role="system",
                content=f"{CHAT_SUMMARY_PREFIX}{history_summary}",
            )

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("post-answer background tasks failed: chat_id=%s", chat_id)
    finally:
        db.close()


router = APIRouter(prefix="/chats", tags=["chats"])
# ---- chats ----


def _require_chat_access(
    chat_id: int,
    db: Session,
    current_user: User,
):
    chat = ChatRepository(db).get(chat_id)
    if not chat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "chat not found")
    if chat.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "chat access denied")
    return chat


# Create a new chat
@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_none=True)

    # title 处理
    title = (data.get("title") or "").strip()
    data["title"] = title or "新会话"

    # ✅ 永远以 token 用户为准，忽略前端传的 user_id（避免 FK 500）
    data["user_id"] = current_user.id

    return ChatRepository(db).create(**data)


# List chats for a user with pagination
@router.get("", response_model=list[ChatOut], include_in_schema=False)
@router.get("/", response_model=list[ChatOut])
def list_chats(
    user_id: int | None = None,
    offset: int = 0,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_user_id = user_id if user_id is not None else current_user.id

    # ✅ 非管理员只能看自己的 chats
    if target_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "chat access denied")

    return ChatRepository(db).list_by_user(target_user_id, offset=offset, limit=limit)


# Update a chat's details
@router.patch("/{chat_id}", response_model=ChatOut)
def update_chat(
    chat_id: int,
    payload: ChatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ChatRepository(db)
    chat = repo.get(chat_id)
    if not chat:
        raise HTTPException(404, "chat not found")

    # ✅ 归属校验
    if chat.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "chat access denied")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return chat

    # title 去空白
    if "title" in updates and updates["title"] is not None:
        t = updates["title"].strip()
        updates["title"] = t or "新会话"

    return repo.update(chat, **updates)


# Delete a chat by ID
@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ChatRepository(db)
    chat = repo.get(chat_id)
    if not chat:
        raise HTTPException(404, "chat not found")

    # ✅ 归属校验
    if chat.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "chat access denied")

    repo.delete(chat_id)

# ---- messages ----

# Create a new message in a chat, chat_id from path parameter
@router.post(
    "/{chat_id}/messages",
    response_model=MessageCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    chat_id: int,
    payload: MessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = MessageRepository(db)
    chat = ChatRepository(db).get(chat_id)
    if not chat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "chat not found")
    if chat.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "chat access denied")

    content = payload.content.strip()
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "content cannot be empty")

    user_message = repo.create(chat_id=chat_id, role=payload.role, content=content)
    assistant_message = None
    reference_models: list[MessageReference] = []

    if payload.role == "user":
        top_k = payload.top_k or DEFAULT_TOP_K
        raw_domain_ids = payload.domain_ids
        domain_ids = (
            sorted({int(domain_id) for domain_id in raw_domain_ids})
            if raw_domain_ids
            else None
        )
        prompt_messages = repo.list_for_prompt(chat_id)
        history_payload = [
            {"role": m.role, "content": m.content}
            for m in prompt_messages
        ]
        memory_messages = repo.list_memory(chat_id)
        memory_chunks = [
            m.content[len(CHUNK_MEMORY_PREFIX) :]
            for m in memory_messages
            if m.content.startswith(CHUNK_MEMORY_PREFIX)
        ]

        try:
            answer_text, references, chunks = answer(
                content,
                domain_ids,
                db=db,
                top_k=top_k,
                history=history_payload,
                memory_chunks=memory_chunks,
                preferred_language=normalize_language_code(payload.language),
            )
        except RuntimeError as exc:
            logger.exception("rag answer failed: chat_id=%s", chat_id)
            answer_text = "抱歉，我暂时无法回答该问题，请确认qdrant服务是否正常运行，或稍后再试。"
            references = []
            chunks = []
        assistant_message = repo.create(chat_id=chat_id, role="assistant", content=answer_text)
        chunk_texts = [chunk_to_memory_text(chunk) for chunk in chunks] if chunks else []
        background_tasks.add_task(
            _run_post_answer_tasks,
            chat_id=chat_id,
            question=content,
            answer_text=answer_text,
            history_payload=history_payload,
            chunk_texts=chunk_texts,
            top_k=top_k,
        )
        reference_models = [
            MessageReference(chunk_id=chunk_id, score=score) for chunk_id, score in references
        ]

    return MessageCreateResponse(
        user=MessageOut.model_validate(user_message),
        assistant=MessageOut.model_validate(assistant_message) if assistant_message else None,
        references=reference_models,
    )

# List messages in a chat with pagination
@router.get("/{chat_id}/messages", response_model=list[MessageOut])
def list_messages(
    chat_id: int,
    offset: int = 0,
    limit: int = Query(200, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_chat_access(chat_id, db, current_user)
    return MessageRepository(db).list_by_chat(chat_id, offset=offset, limit=limit)

# Update a message's content, identified by message ID
@router.patch("/messages/{msg_id}", response_model=MessageOut)
def update_message(
    msg_id: int,
    payload: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = MessageRepository(db)
    m = repo.get(msg_id)
    if not m:
        raise HTTPException(404, "message not found")
    _require_chat_access(m.chat_id, db, current_user)
    return repo.update(m, **payload.model_dump(exclude_none=True))

# Delete a message by ID, identified by message ID
@router.delete("/messages/{msg_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    msg_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = MessageRepository(db)
    message = repo.get(msg_id)
    if not message:
        raise HTTPException(404, "message not found")
    _require_chat_access(message.chat_id, db, current_user)
    repo.delete(msg_id)
