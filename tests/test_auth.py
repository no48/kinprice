"""Basic認証の動作テスト。"""
import base64

import pytest

from app import create_app


@pytest.fixture
def app():
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def get_prefix(app):
    return app.config.get("URL_PREFIX", "/gold-admin")


def _auth_header(username: str, password: str) -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_index_without_auth_returns_401(client, app):
    prefix = get_prefix(app)
    res = client.get(f"{prefix}/")
    assert res.status_code == 401


def test_index_with_valid_auth_returns_200(client, app):
    prefix = get_prefix(app)
    res = client.get(f"{prefix}/", headers=_auth_header("testuser", "testpass"))
    assert res.status_code == 200


def test_index_with_invalid_auth_returns_401(client, app):
    prefix = get_prefix(app)
    res = client.get(f"{prefix}/", headers=_auth_header("wrong", "wrong"))
    assert res.status_code == 401


def test_fetch_without_auth_returns_401(client, app):
    prefix = get_prefix(app)
    res = client.post(f"{prefix}/fetch")
    assert res.status_code == 401


def test_upload_without_auth_returns_401(client, app):
    prefix = get_prefix(app)
    res = client.post(f"{prefix}/upload")
    assert res.status_code == 401
