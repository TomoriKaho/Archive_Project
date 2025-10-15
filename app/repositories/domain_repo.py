from sqlalchemy import select
from sqlalchemy.orm import Session
from .base import Repository
from app.models.entities import Domain

class DomainRepository(Repository[Domain]):
    def __init__(self, db: Session):
        super().__init__(db, Domain)

    def get_by_name(self, name: str) -> Domain | None:
        stmt = select(Domain).where(Domain.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_or_create(self, name: str, description: str | None = None) -> Domain:
        dom = self.get_by_name(name)
        if dom:
            return dom
        return self.create(name=name, description=description)
