from pathlib import Path
import hashlib
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services import password_guard


class FakeResponse:
    def __init__(self, body: str):
        self._body = body.encode('utf-8')

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_is_password_compromised_detects_match(monkeypatch):
    password = 'Compromised123!'
    sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    def fake_urlopen(url, timeout=5):
        assert url.endswith(prefix)
        return FakeResponse(f'{suffix}:42')

    monkeypatch.setattr(password_guard.request, 'urlopen', fake_urlopen)

    assert password_guard.is_password_compromised(password) is True


def test_is_password_compromised_handles_network_error(monkeypatch):
    def fake_urlopen(url, timeout=5):  # noqa: ARG001
        raise OSError('network down')

    monkeypatch.setattr(password_guard.request, 'urlopen', fake_urlopen)

    assert password_guard.is_password_compromised('AnyPassword!') is False
