from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services import password_guard


@pytest.mark.parametrize(
    "password",
    [
        "password",  # 无数字
        "12345678",  # 无字母
        "Abc123",  # 长度不足
        "Abc123!!",  # 包含特殊符号
        "",  # 空字符串
    ],
)
def test_password_policy_rejects_invalid_passwords(password):
    assert password_guard.is_password_compromised(password) is True


@pytest.mark.parametrize(
    "password",
    [
        "Password123",
        "abcXYZ789",
        "A1B2C3D4",
    ],
)
def test_password_policy_accepts_valid_passwords(password):
    assert password_guard.is_password_compromised(password) is False
