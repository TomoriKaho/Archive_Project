from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.domain import DomainCreate, DomainUpdate, DomainOut
from app.repositories.domain_repo import DomainRepository


router = APIRouter(prefix="/domains", tags=["domains"])

# ---- domains ----
# Create domain
@router.post("", response_model=DomainOut, status_code=status.HTTP_201_CREATED)
def create_domain(payload: DomainCreate, db: Session = Depends(get_db)):
    repo = DomainRepository(db)
    if repo.get_by_name(payload.name):
        raise HTTPException(400, "domain name already exists")
    return repo.create(name=payload.name, description=payload.description)

# List domains
@router.get("", response_model=list[DomainOut])
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

    