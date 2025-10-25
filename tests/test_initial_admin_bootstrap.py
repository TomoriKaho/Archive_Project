from __future__ import annotations

from types import SimpleNamespace

from app.core.config import INITIAL_ADMIN_EMAIL
from app.services import initial_admin


class DummyRepo:
    def __init__(self, user):
        self._user = user
        self.created_payload = None
        self.updated_payload = None

    def get_by_email(self, email):  # noqa: D401
        assert email == INITIAL_ADMIN_EMAIL
        return self._user

    def create_user(self, **data):  # noqa: D401, ANN003
        self.created_payload = data
        return SimpleNamespace(id=1, **data)

    def update(self, user, **data):  # noqa: D401, ANN003
        self.updated_payload = (user, data)
        return user


def test_ensure_initial_admin_creates_missing_account(monkeypatch):
    repo = DummyRepo(user=None)
    monkeypatch.setattr(initial_admin, "UserRepository", lambda db: repo)
    monkeypatch.setattr(initial_admin, "hash_password", lambda password: f"hash::{password}")
    monkeypatch.setenv("ADMIN_INIT_PASSWORD", "SuperSecret!123")

    initial_admin.ensure_initial_admin(db=None)

    assert repo.created_payload == {
        "email": INITIAL_ADMIN_EMAIL,
        "hashed_password": "hash::SuperSecret!123",
        "is_admin": True,
        "full_name": "Administrator",
    }
    assert repo.updated_payload is None


def test_ensure_initial_admin_restores_admin_flag(monkeypatch):
    existing = SimpleNamespace(is_admin=False)
    repo = DummyRepo(user=existing)
    monkeypatch.setattr(initial_admin, "UserRepository", lambda db: repo)

    initial_admin.ensure_initial_admin(db=None)

    assert repo.created_payload is None
    assert repo.updated_payload[0] is existing
    assert repo.updated_payload[1] == {"is_admin": True}


def test_ensure_initial_admin_uses_default_password_warning(monkeypatch, caplog):
    repo = DummyRepo(user=None)
    monkeypatch.setattr(initial_admin, "UserRepository", lambda db: repo)
    monkeypatch.setattr(initial_admin, "hash_password", lambda password: password)
    monkeypatch.delenv("ADMIN_INIT_PASSWORD", raising=False)

    with caplog.at_level("WARNING"):
        initial_admin.ensure_initial_admin(db=None)

    assert repo.created_payload["hashed_password"] == initial_admin.DEFAULT_ADMIN_PASSWORD
    assert any("ADMIN_INIT_PASSWORD" in message for message in caplog.messages)
