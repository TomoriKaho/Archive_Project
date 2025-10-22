import argparse
from sqlalchemy import select
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.entities import User

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    args = p.parse_args()

    with SessionLocal() as db:
        exists = db.execute(select(User).where(User.email == args.email.lower())).scalar_one_or_none()
        if exists:
            print(f"User {args.email} already exists (is_admin={exists.is_admin}). Skipped.")
            return
        admin = User(email=args.email.lower(), hashed_password=hash_password(args.password), is_admin=True)
        db.add(admin)
        db.flush()
        print(f"✅ Admin seeded: id={admin.id}, email={admin.email}")

if __name__ == "__main__":
    main()
