"""Seed or update an administrator user in the database."""
from argparse import ArgumentParser, Namespace
from getpass import getpass

from pydantic import ValidationError

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate


def _build_payload(args: Namespace, parser: ArgumentParser) -> UserCreate:
    """Validate parsed CLI arguments against the ``UserCreate`` schema."""

    password = args.password or getpass("Admin password: ")

    try:
        return UserCreate(email=args.email, password=password, is_admin=True)
    except ValidationError as exc:  # pragma: no cover - user input validation
        messages = [
            "{}: {}".format(".".join(str(part) for part in error["loc"]), error["msg"])
            for error in exc.errors()
        ]
        parser.error("; ".join(messages))
        raise SystemExit(2)


def main() -> None:
    parser = ArgumentParser(description="Create or update an administrator account.")
    parser.add_argument("--email", required=True, help="Administrator email address")
    parser.add_argument(
        "--password",
        help="Administrator password. If omitted, you will be prompted securely.",
    )

    args = parser.parse_args()
    payload = _build_payload(args, parser)

    session = SessionLocal()
    try:
        repo = UserRepository(session)
        hashed_password = get_password_hash(payload.password)
        existing = repo.get_by_email(payload.email)
        if existing:
            repo.update(existing, hashed_password=hashed_password, is_admin=True)
            action = "updated"
        else:
            repo.create_user(
                email=payload.email, hashed_password=hashed_password, is_admin=True
            )
            action = "created"
        session.commit()
        print(f"Admin user {payload.email} {action} successfully.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
