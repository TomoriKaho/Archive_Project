"""Seed or update an administrator user in the database."""
from argparse import ArgumentParser
from getpass import getpass

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.repositories.user_repo import UserRepository


def main() -> None:
    parser = ArgumentParser(description="Create or update an administrator account.")
    parser.add_argument("--email", required=True, help="Administrator email address")
    parser.add_argument(
        "--password",
        help="Administrator password. If omitted, you will be prompted securely.",
    )
    args = parser.parse_args()

    password = args.password or getpass("Admin password: ")

    session = SessionLocal()
    try:
        repo = UserRepository(session)
        hashed_password = get_password_hash(password)
        existing = repo.get_by_email(args.email)
        if existing:
            repo.update(existing, hashed_password=hashed_password, is_admin=True)
            action = "updated"
        else:
            repo.create_user(
                email=args.email, hashed_password=hashed_password, is_admin=True
            )
            action = "created"
        session.commit()
        print(f"Admin user {args.email} {action} successfully.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
