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

def test_upload_rejects_non_numeric_retail_price(client, app):
    prefix = get_prefix(app)
    payload = {"retail_price": "abc", "purchase_price": "25,000", "date": "2026/04/04"}
    res = client.post(
        f"{prefix}/upload",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_upload_rejects_non_numeric_purchase_price(client, app):
    prefix = get_prefix(app)
    payload = {"retail_price": "26,200", "purchase_price": "invalid!", "date": "2026/04/04"}
    res = client.post(
        f"{prefix}/upload",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_upload_defaults_purchase_price_to_retail(client, app):
    prefix = get_prefix(app)
    payload = {"retail_price": "26,200", "purchase_price": "", "date": "2026/04/04"}
    wp_result = {"success": True, "message": "OK"}
    with patch("app.routes.update_gold_page", return_value=wp_result) as mock_wp:
        res = client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
    call_kwargs = mock_wp.call_args[1]
    assert call_kwargs["purchase_price"] == "26,200"


# ---------------------------------------------------------------------------
# /upload - WordPress posting
# ---------------------------------------------------------------------------

def test_upload_posts_to_wordpress(client, app):
    prefix = get_prefix(app)
    payload = {"retail_price": "26,200", "purchase_price": "25,000", "date": "2026/04/04"}
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
    payload = {
        "retail_price": "26,200",
        "purchase_price": "25,000",
        "date": "2026/04/04",
        "post_to_wp": False,
    }
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
    payload = {"retail_price": "26,200", "purchase_price": "25,000", "date": "4月4日"}
    wp_result = {"success": True, "message": "OK"}
    with patch("app.routes.update_gold_page", return_value=wp_result):
        res = client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
    data = res.get_json()
    assert "gbp_text" in data
    assert "25,000" in data["gbp_text"]
    assert "4月4日" in data["gbp_text"]


def test_upload_returns_gbp_search_url(client, app):
    prefix = get_prefix(app)
    payload = {"retail_price": "26,200", "purchase_price": "25,000", "date": "4月4日"}
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
