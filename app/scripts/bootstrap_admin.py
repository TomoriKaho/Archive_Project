"""命令行脚本：确保初始管理员存在。"""
from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.services.initial_admin import ensure_initial_admin


def main() -> None:
    """Entry point used via ``python -m app.scripts.bootstrap_admin``."""

    logging.basicConfig(level=logging.INFO)
    session = SessionLocal()
    try:
        ensure_initial_admin(session)
        session.commit()
    except Exception:  # pragma: no cover - 命令行脚本保留完整回滚流程
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":  # pragma: no cover - 脚本入口不计入覆盖率
    main()
