import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.api import auth as auth_api
from app.api import users as users_api
from app.core.config import INITIAL_ADMIN_EMAIL
from app.schemas.user import UserCreate


class DummyRepo:
    def __init__(self, user_to_return=None):
        self._user = user_to_return
        self.deleted_id = None

    def get_by_email(self, email):  # noqa: ARG002
        return None

    def create_user(self, **kwargs):  # noqa: D401, ANN003
        self.created = kwargs
        return SimpleNamespace(**kwargs, id=1)

    def get(self, user_id):  # noqa: ARG002
        return self._user

    def delete(self, user_id):
        self.deleted_id = user_id


def test_register_rejects_compromised_password(monkeypatch):
    monkeypatch.setattr(auth_api, 'UserRepository', lambda db: DummyRepo())
    monkeypatch.setattr(auth_api, 'is_password_compromised', lambda password: True)

    payload = UserCreate(email='user@example.com', password='WeakPassword1', full_name=None)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(auth_api.register(payload, db=None))

    assert excinfo.value.status_code == 400
    assert '密码存在泄露风险' in excinfo.value.detail


def test_delete_user_blocks_admin_removal_without_initial_privilege(monkeypatch):
    target_user = SimpleNamespace(id=2, email='admin2@example.com', is_admin=True)
    repo = DummyRepo(user_to_return=target_user)
    monkeypatch.setattr(users_api, 'UserRepository', lambda db: repo)

    current_admin = SimpleNamespace(id=1, email='other_admin@example.com', is_admin=True)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(users_api.delete_user(2, current_admin=current_admin, db=None))

    assert excinfo.value.status_code == 403
    assert repo.deleted_id is None


def test_delete_user_blocks_initial_admin_account(monkeypatch):
    target_user = SimpleNamespace(id=5, email=INITIAL_ADMIN_EMAIL, is_admin=True)
    repo = DummyRepo(user_to_return=target_user)
    monkeypatch.setattr(users_api, 'UserRepository', lambda db: repo)

    current_admin = SimpleNamespace(id=1, email=INITIAL_ADMIN_EMAIL, is_admin=True)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(users_api.delete_user(5, current_admin=current_admin, db=None))

    assert excinfo.value.status_code == 403
    assert repo.deleted_id is None


def test_initial_admin_can_delete_other_admin(monkeypatch):
    target_user = SimpleNamespace(id=7, email='another_admin@example.com', is_admin=True)
    repo = DummyRepo(user_to_return=target_user)
    monkeypatch.setattr(users_api, 'UserRepository', lambda db: repo)

    current_admin = SimpleNamespace(id=1, email=INITIAL_ADMIN_EMAIL, is_admin=True)

    response = asyncio.run(users_api.delete_user(7, current_admin=current_admin, db=None))

    assert response.status_code == 204
    assert repo.deleted_id == 7
