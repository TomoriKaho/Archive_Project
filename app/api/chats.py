import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.chat import ChatCreate, ChatUpdate, ChatOut
from app.schemas.message import MessageCreate, MessageUpdate, MessageOut
from app.schemas.rag import RagMessageResponse, RagSource
from app.repositories.chat_repo import ChatRepository
from app.repositories.message_repo import MessageRepository
from app.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

pipeline = RAGPipeline()

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
    response_model=MessageOut | RagMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(chat_id: int, payload: MessageCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_none=True)
    data["chat_id"] = chat_id  # 路径参数优先生效
    repo = MessageRepository(db)
    message = repo.create(**data)
    if payload.role != "user":
        return message
    try:
        result = pipeline.run(payload.content)
    except Exception as exc:  # pragma: no cover - 调用外部服务异常
        logger.exception("rag pipeline execution failed chat_id=%s", chat_id)
        raise HTTPException(status_code=500, detail="failed to generate assistant response") from exc
    message_metadata = pipeline.build_metadata(result.sources)
    assistant = repo.create(
        chat_id=chat_id,
        role="assistant",
        content=result.answer,
        message_metadata=message_metadata,
    )
    sources = [RagSource.model_validate(source.to_source_metadata()) for source in result.sources]
    return RagMessageResponse(
        question=MessageOut.model_validate(message),
        answer=MessageOut.model_validate(assistant),
        sources=sources,
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
