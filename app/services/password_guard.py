"""密码安全检测工具，避免使用已知泄露的弱密码。"""
from __future__ import annotations

import hashlib
import logging
from typing import Final
from urllib import request

logger = logging.getLogger(__name__)

HIBP_API_PREFIX: Final[str] = "https://api.pwnedpasswords.com/range/"


def is_password_compromised(password: str) -> bool:
    """使用 Have I Been Pwned 的匿名查询接口检测密码是否出现在泄露列表中。"""
    if not password:
        return False
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    try:
        with request.urlopen(f"{HIBP_API_PREFIX}{prefix}", timeout=5) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:  # 网络错误或服务不可用时直接跳过
        logger.warning("无法访问泄露密码库，跳过检测", exc_info=exc)
        return False
    for line in body.splitlines():
        try:
            hash_suffix, _count = line.split(":")
        except ValueError:  # 忽略异常行
            continue
        if hash_suffix == suffix:
            return True
    return False
