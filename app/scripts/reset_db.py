from app.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE;"))
    conn.execute(text("CREATE SCHEMA public;"))
    print("✅ Database schema 'public' has been reset.")