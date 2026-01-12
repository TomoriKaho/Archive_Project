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

    def get_or_create(
        self,
        name: str,
        description: str | None = None,
        language: str | None = None,
    ) -> Domain:
        dom = self.get_by_name(name)
        if dom:
            return dom
        return self.create(name=name, description=description, language=language)

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        sort_by: str = "name",
        order: str = "asc",
    ) -> list[Domain]:
        if sort_by == "description":
            sort_column = Domain.description
        elif sort_by == "language":
            sort_column = Domain.language
        elif sort_by == "created_at":
            sort_column = Domain.created_at
        elif sort_by == "updated_at":
            sort_column = Domain.updated_at
        else:
            sort_column = Domain.name
        sort_expression = sort_column.asc() if order == "asc" else sort_column.desc()
        stmt = (
            select(Domain)
            .order_by(sort_expression, Domain.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
