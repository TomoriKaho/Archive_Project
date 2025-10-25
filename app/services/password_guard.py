"""密码安全检测工具，确保注册与修改密码符合复杂度要求。"""
from __future__ import annotations

import re
from typing import Final

PASSWORD_POLICY_MESSAGE: Final[str] = "密码必须至少 8 位，同时包含字母和数字，并且不能包含特殊符号。"
_PASSWORD_POLICY: Final[re.Pattern[str]] = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$")


def is_password_compromised(password: str) -> bool:
    """检测密码是否违反复杂度要求。返回 True 表示密码不符合规范。"""
    if not password:
        return True
    return _PASSWORD_POLICY.fullmatch(password) is None
