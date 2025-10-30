import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
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
from app.services.rag_service import DEFAULT_TOP_K, answer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["chats"])
# ---- chats ----

# Create a new chat
@router.post("/", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def create_chat(payload: ChatCreate, db: Session = Depends(get_db)):
    return ChatRepository(db).create(**payload.model_dump())

# List chats for a user with pagination
@router.get("/", response_model=list[ChatOut])
def list_chats(user_id: int, offset: int = 0, limit: int = Query(50, le=200), db: Session = Depends(get_db)):
    return ChatRepository(db).list_by_user(user_id, offset=offset, limit=limit)

# Update a chat's details
@router.patch("/{chat_id}", response_model=ChatOut)
def update_chat(chat_id: int, payload: ChatUpdate, db: Session = Depends(get_db)):
    repo = ChatRepository(db)
    chat = repo.get(chat_id)
    if not chat:
        raise HTTPException(404, "chat not found")
    return repo.update(chat, **payload.model_dump(exclude_none=True))

# Delete a chat by ID
@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: int, db: Session = Depends(get_db)):
    if not ChatRepository(db).get(chat_id):
        raise HTTPException(404, "chat not found")
    ChatRepository(db).delete(chat_id)

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
        domain_ids = sorted(set(payload.domain_ids)) if payload.domain_ids else None
        try:
            answer_text, references = answer(
                content,
                domain_ids,
                db=db,
                top_k=top_k,
            )
        except RuntimeError as exc:
            logger.exception("rag answer failed: chat_id=%s", chat_id)
            answer_text = "抱歉，我暂时无法回答该问题。"
            references = []
        assistant_message = repo.create(chat_id=chat_id, role="assistant", content=answer_text)
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
def list_messages(chat_id: int, offset: int = 0, limit: int = Query(200, le=500), db: Session = Depends(get_db)):
    return MessageRepository(db).list_by_chat(chat_id, offset=offset, limit=limit)

# Update a message's content, identified by message ID
@router.patch("/messages/{msg_id}", response_model=MessageOut)
def update_message(msg_id: int, payload: MessageUpdate, db: Session = Depends(get_db)):
    repo = MessageRepository(db)
    m = repo.get(msg_id)
    if not m:
        raise HTTPException(404, "message not found")
    return repo.update(m, **payload.model_dump(exclude_none=True))

# Delete a message by ID, identified by message ID
@router.delete("/messages/{msg_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(msg_id: int, db: Session = Depends(get_db)):
    if not MessageRepository(db).get(msg_id):
        raise HTTPException(404, "message not found")
    MessageRepository(db).delete(msg_id)
