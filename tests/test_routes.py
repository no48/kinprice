"""Tests for Flask routes."""
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
    mock_result = {"retail_price": "26,200", "purchase_price": "25,000", "date": "2026/04/02 11:30"}
    with patch("app.routes.scrape_gold_price", return_value=mock_result):
        res = client.post(f"{prefix}/fetch")
    assert res.status_code == 200
    data = res.get_json()
    assert data["retail_price"] == "26,200"
    assert data["date"] == "2026/04/02 11:30"


def test_fetch_returns_error_on_exception(client, app):
    prefix = get_prefix(app)
    with patch("app.routes.scrape_gold_price", side_effect=Exception("network error")):
        res = client.post(f"{prefix}/fetch")
    assert res.status_code == 500
    data = res.get_json()
    assert "error" in data
    assert "network error" in data["error"]


# ---------------------------------------------------------------------------
# /upload - input validation
# ---------------------------------------------------------------------------

def test_upload_rejects_non_numeric_retail_price(client, app):
    prefix = get_prefix(app)
    payload = {"retail_price": "abc", "purchase_price": "25,000", "date": "2026/04/02 11:30"}
    res = client.post(
        f"{prefix}/upload",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data


def test_upload_rejects_non_numeric_purchase_price(client, app):
    prefix = get_prefix(app)
    payload = {"retail_price": "26,200", "purchase_price": "invalid!", "date": "2026/04/02 11:30"}
    res = client.post(
        f"{prefix}/upload",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data


def test_upload_accepts_valid_prices(client, app):
    prefix = get_prefix(app)
    payload = {
        "retail_price": "26,200",
        "purchase_price": "25,000",
        "date": "2026/04/02 11:30",
        "post_to_wp": True,
        "post_to_google": False,
    }
    wp_result = {"success": True, "message": "WordPress更新成功"}
    with patch("app.routes.update_gold_page", return_value=wp_result):
        res = client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
    assert res.status_code == 200
    data = res.get_json()
    assert "wordpress" in data
    assert data["wordpress"]["success"] is True


def test_upload_skips_wp_when_flag_false(client, app):
    prefix = get_prefix(app)
    payload = {
        "retail_price": "26,200",
        "purchase_price": "25,000",
        "date": "2026/04/02 11:30",
        "post_to_wp": False,
        "post_to_google": False,
    }
    with patch("app.routes.update_gold_page") as mock_wp:
        res = client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
        mock_wp.assert_not_called()
    assert res.status_code == 200


def test_upload_google_error_is_captured(client, app):
    prefix = get_prefix(app)
    payload = {
        "retail_price": "26,200",
        "purchase_price": "25,000",
        "date": "2026/04/02 11:30",
        "post_to_wp": False,
        "post_to_google": True,
    }
    with patch("app.routes.get_service", side_effect=Exception("credentials not found")):
        res = client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
    assert res.status_code == 200
    data = res.get_json()
    assert "google" in data
    assert data["google"]["success"] is False
    assert "Google投稿エラー" in data["google"]["error"]
