"""应用级配置常量，集中维护环境变量读取逻辑。"""
from __future__ import annotations

import os

# 初始管理员邮箱，用于限制高危操作，仅允许该账号执行部分敏感操作。
INITIAL_ADMIN_EMAIL: str = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
