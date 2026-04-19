"""Tests for Flask routes."""
import base64
import json
from unittest.mock import patch

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


@pytest.fixture(autouse=True)
def auth_headers(client):
    """全てのテストリクエストにBasic認証ヘッダを自動付与する。"""
    token = base64.b64encode(b"testuser:testpass").decode()
    client.environ_base["HTTP_AUTHORIZATION"] = f"Basic {token}"
    return client


def get_prefix(app):
    return app.config.get("URL_PREFIX", "/gold-admin")


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------

def test_index_returns_200(client, app):
    prefix = get_prefix(app)
    res = client.get(f"{prefix}/")
    assert res.status_code == 200


def test_index_contains_title(client, app):
    prefix = get_prefix(app)
    res = client.get(f"{prefix}/")
    assert "金価格" in res.data.decode("utf-8")


# ---------------------------------------------------------------------------
# /fetch
# ---------------------------------------------------------------------------

def test_fetch_returns_json(client, app):
    prefix = get_prefix(app)
    mock_result = {"retail_price": "26,200", "date": "2026/04/06 09:30"}
    with patch("app.routes.scrape_gold_price", return_value=mock_result):
        res = client.post(f"{prefix}/fetch")
    assert res.status_code == 200
    data = res.get_json()
    assert data["retail_price"] == "26,200"


def test_fetch_returns_error_on_exception(client, app):
    prefix = get_prefix(app)
    with patch("app.routes.scrape_gold_price", side_effect=Exception("network error")):
        res = client.post(f"{prefix}/fetch")
    assert res.status_code == 500
    assert "error" in res.get_json()


# ---------------------------------------------------------------------------
# /upload - validation
# ---------------------------------------------------------------------------

def _valid_payload(**overrides):
    payload = {
        "date": "2026/04/04",
        "gold_scrap": {"K24": "25,000", "K18": "19,000", "K14": "14,000"},
        "pt_scrap": {"Pt1000": "11,000", "Pt900": "10,000", "Pt850": "9,000"},
    }
    payload.update(overrides)
    return payload


def test_upload_rejects_non_numeric_scrap_price(client, app):
    prefix = get_prefix(app)
    payload = _valid_payload(gold_scrap={"K24": "invalid!", "K18": "19,000", "K14": "14,000"})
    res = client.post(
        f"{prefix}/upload",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# /upload - WordPress posting
# ---------------------------------------------------------------------------

def test_upload_posts_to_wordpress(client, app):
    prefix = get_prefix(app)
    payload = _valid_payload()
    wp_result = {"success": True, "message": "WordPress更新成功", "link": "https://example.com/gold"}
    with patch("app.routes.update_gold_page", return_value=wp_result):
        res = client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
    assert res.status_code == 200
    data = res.get_json()
    assert data["wordpress"]["success"] is True


def test_upload_skips_wp_when_flag_false(client, app):
    prefix = get_prefix(app)
    payload = _valid_payload(post_to_wp=False)
    with patch("app.routes.update_gold_page") as mock_wp:
        res = client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
        mock_wp.assert_not_called()
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# /upload - GBP text
# ---------------------------------------------------------------------------

def test_upload_returns_gbp_text(client, app):
    prefix = get_prefix(app)
    payload = _valid_payload(date="4月4日")
    wp_result = {"success": True, "message": "OK"}
    with patch("app.routes.update_gold_page", return_value=wp_result):
        res = client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
    data = res.get_json()
    assert "gbp_text" in data
    assert "19,000" in data["gbp_text"]
    assert "4月4日" in data["gbp_text"]


def test_upload_returns_gbp_search_url(client, app):
    prefix = get_prefix(app)
    payload = _valid_payload()
    wp_result = {"success": True, "message": "OK"}
    with patch("app.routes.update_gold_page", return_value=wp_result):
        res = client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
    data = res.get_json()
    assert "gbp_search_url" in data
    assert "google.com/search" in data["gbp_search_url"]
