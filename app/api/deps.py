from app.db.session import SessionLocal

def get_db():
    # FastAPI 的依赖：yield 一个可用的 Session，自动提交/回滚由 SessionLocal 管
    with SessionLocal() as db:
        yield db
