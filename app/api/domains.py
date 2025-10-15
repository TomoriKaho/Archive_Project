from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.domain import DomainCreate, DomainUpdate, DomainOut
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentOut
from app.schemas.chunk import ChunkOut
from app.repositories.domain_repo import DomainRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.chunk_repo import ChunkRepository

router = APIRouter(prefix="/domains", tags=["domains"])

# ---- domains ----
# Create domain
@router.post("/", response_model=DomainOut, status_code=status.HTTP_201_CREATED)
def create_domain(payload: DomainCreate, db: Session = Depends(get_db)):
    repo = DomainRepository(db)
    if repo.get_by_name(payload.name):
        raise HTTPException(400, "domain name already exists")
    return repo.create(name=payload.name, description=payload.description)

# List domains
@router.get("/", response_model=list[DomainOut])
def list_domains(
    db: Session = Depends(get_db),
    offset: int = 0,
    limit: int = Query(100, le=200),
):
    return DomainRepository(db).list(offset=offset, limit=limit)

# Get domain by ID
@router.get("/{domain_id}", response_model=DomainOut)
def get_domain(domain_id: int, db: Session = Depends(get_db)):
    dom = DomainRepository(db).get(domain_id)
    if not dom:
        raise HTTPException(404, "domain not found")
    return dom

# Update domain, partial update, only non-null fields in payload will be updated
@router.patch("/{domain_id}", response_model=DomainOut)
def update_domain(domain_id: int, payload: DomainUpdate, db: Session = Depends(get_db)):
    repo = DomainRepository(db)
    dom = repo.get(domain_id)
    if not dom:
        raise HTTPException(404, "domain not found")
    return repo.update(dom, **payload.model_dump(exclude_none=True))

# Delete domain, also delete all related documents and chunks
@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(domain_id: int, db: Session = Depends(get_db)):
    if not DomainRepository(db).get(domain_id):
        raise HTTPException(404, "domain not found")
    DomainRepository(db).delete(domain_id)

# ---- documents ----

# Create document under a domain
@router.post("/{domain_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(domain_id: int, payload: DocumentCreate, db: Session = Depends(get_db)):
    # 强制以路径中的 domain_id 为准，避免越权写入其他 domain
    data = payload.model_dump()
    data["domain_id"] = domain_id
    return DocumentRepository(db).create(**data)

# List documents under a domain
@router.get("/{domain_id}/documents", response_model=list[DocumentOut])
def list_documents(domain_id: int, offset: int = 0, limit: int = Query(50, le=200), db: Session = Depends(get_db)):
    return DocumentRepository(db).list_by_domain(domain_id, offset=offset, limit=limit)

# Get document by ID, independent of domain
@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = DocumentRepository(db).get(doc_id)
    if not doc:
        raise HTTPException(404, "document not found")
    return doc

# Update document, partial update, only non-null fields in payload will be updated
@router.patch("/documents/{doc_id}", response_model=DocumentOut)
def update_document(doc_id: int, payload: DocumentUpdate, db: Session = Depends(get_db)):
    repo = DocumentRepository(db)
    doc = repo.get(doc_id)
    if not doc:
        raise HTTPException(404, "document not found")
    return repo.update(doc, **payload.model_dump(exclude_none=True))

# Delete document, also delete all related chunks
@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    DocumentRepository(db).delete(doc_id)

# ---- chunks ----
# Create chunk under a document, independent of domain
# (In practice, chunk are automatically created when ingesting documents, 
# so this API is rarely used, so as update and delete)
@router.post("/documents/{doc_id}/chunks", response_model=ChunkOut, status_code=status.HTTP_201_CREATED)
def create_chunk(doc_id: int, payload: DocumentCreate, db: Session = Depends(get_db)):
    # 强制以路径中的 doc_id 为准，避免越权写入其他 document
    data = payload.model_dump()
    data["document_id"] = doc_id
    return ChunkRepository(db).create(**data)   

# List chunks under a document, independent of domain
@router.get("/documents/{doc_id}/chunks", response_model=list[ChunkOut])
def list_chunks(doc_id: int, db: Session = Depends(get_db)):
    return ChunkRepository(db).list_by_document(doc_id)

# Get chunk by ID, independent of document and domain
@router.get("/chunks/{chunk_id}", response_model=ChunkOut)
def get_chunk(chunk_id: int, db: Session = Depends(get_db)):
    chunk = ChunkRepository(db).get(chunk_id)
    if not chunk:
        raise HTTPException(404, "chunk not found")
    return chunk

# Update chunk by ID, independent of document and domain
@router.patch("/chunks/{chunk_id}", response_model=ChunkOut)
def update_chunk(chunk_id: int, payload: DocumentUpdate, db: Session = Depends(get_db)):
    repo = ChunkRepository(db)
    chunk = repo.get(chunk_id)
    if not chunk:
        raise HTTPException(404, "chunk not found")
    return repo.update(chunk, **payload.model_dump(exclude_none=True))

# Delete chunk by ID, independent of document and domain
@router.delete("/chunks/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chunk(chunk_id: int, db: Session = Depends(get_db)):
    if not ChunkRepository(db).get(chunk_id):
        raise HTTPException(404, "chunk not found")
    ChunkRepository(db).delete(chunk_id)

    