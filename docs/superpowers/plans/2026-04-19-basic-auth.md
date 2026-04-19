# Basic 認証導入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gold-price-uploader Flask アプリの全ルートに Basic 認証をかけ、Render本番環境で第三者アクセスを防止する。

**Architecture:** `Flask-HTTPAuth` を導入し、Blueprint の `before_request` フックで全ルートに認証を適用する。認証情報は環境変数 `BASIC_AUTH_USERNAME` / `BASIC_AUTH_PASSWORD` で管理する。

**Tech Stack:** Flask 3.1.0, Flask-HTTPAuth, python-dotenv, pytest

## File Structure

| ファイル | 変更 | 責務 |
|---|---|---|
| `requirements.txt` | Modify | `Flask-HTTPAuth` 追加 |
| `app/config.py` | Modify | Basic認証の環境変数読み込み |
| `app/__init__.py` | Modify | `HTTPBasicAuth` 初期化 + Blueprint全ルートに認証適用 |
| `render.yaml` | Modify | 環境変数 `BASIC_AUTH_USERNAME` / `BASIC_AUTH_PASSWORD` を追加 |
| `tests/conftest.py` | Modify | テスト用の認証情報をenv varsに設定 |
| `tests/test_routes.py` | Modify | 全リクエストにBasic認証ヘッダを付与 |
| `tests/test_auth.py` | Create | Basic認証の動作テスト（成功・失敗ケース） |

---

## Task 1: `requirements.txt` に Flask-HTTPAuth を追加

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Flask-HTTPAuth を追加**

`requirements.txt` の末尾に追加：

```
Flask-HTTPAuth==4.8.0
```

- [ ] **Step 2: インストール**

Run: `pip install Flask-HTTPAuth==4.8.0`
Expected: `Successfully installed Flask-HTTPAuth-4.8.0`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: Flask-HTTPAuth依存を追加"
```

---

## Task 2: `app/config.py` に Basic 認証の環境変数を追加

**Files:**
- Modify: `app/config.py`

- [ ] **Step 1: Config クラスに環境変数を追加**

`app/config.py` の `Config` クラスに以下を追加（`GBP` セクションの後）：

```python
    # Basic認証
    BASIC_AUTH_USERNAME = os.environ["BASIC_AUTH_USERNAME"]
    BASIC_AUTH_PASSWORD = os.environ["BASIC_AUTH_PASSWORD"]
```

変更後の完全な `app/config.py`：

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ["FLASK_SECRET_KEY"]
    URL_PREFIX = os.environ.get("APP_URL_PREFIX", "/gold-admin")

    # WordPress
    WP_SITE_URL = os.environ["WP_SITE_URL"]
    WP_USERNAME = os.environ["WP_USERNAME"]
    WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]
    WP_PAGE_ID = int(os.environ["WP_PAGE_ID"])

    # スクレイピング
    GOLD_SOURCE_URL = os.environ.get(
        "GOLD_SOURCE_URL",
        "https://www.net-japan.co.jp/precious_metal_partner/",
    )

    # GBP
    GBP_SEARCH_URL = os.environ.get(
        "GBP_SEARCH_URL",
        "https://www.google.com/search?q=フリマハイクラス",
    )

    # Basic認証
    BASIC_AUTH_USERNAME = os.environ["BASIC_AUTH_USERNAME"]
    BASIC_AUTH_PASSWORD = os.environ["BASIC_AUTH_PASSWORD"]
```

- [ ] **Step 2: commit (テストはTask 5以降)**

```bash
git add app/config.py
git commit -m "feat: Basic認証用の環境変数を読み込む"
```

---

## Task 3: `tests/conftest.py` にテスト用認証情報を追加

**Files:**
- Modify: `tests/conftest.py`

**理由:** Task 2 で `BASIC_AUTH_USERNAME` / `BASIC_AUTH_PASSWORD` が必須になったため、テスト環境でも設定しないと `create_app()` が KeyError で失敗する。

- [ ] **Step 1: conftest.py に環境変数を追加**

`tests/conftest.py` の完全な内容に置き換え：

```python
import os

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
os.environ.setdefault("WP_SITE_URL", "https://example.com")
os.environ.setdefault("WP_USERNAME", "admin")
os.environ.setdefault("WP_APP_PASSWORD", "xxxx-xxxx-xxxx-xxxx")
os.environ.setdefault("WP_PAGE_ID", "123")
os.environ.setdefault("GBP_SEARCH_URL", "https://www.google.com/search?q=test")
os.environ.setdefault("BASIC_AUTH_USERNAME", "testuser")
os.environ.setdefault("BASIC_AUTH_PASSWORD", "testpass")
```

- [ ] **Step 2: 既存テストが（認証未対応のため）失敗することを確認する前に、まず既存テストは現時点ではまだ認証が適用されていないのでpassするはず**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && pytest tests/test_routes.py -v`
Expected: 全テストがPASS（認証はまだ未実装なので既存動作のまま）

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: Basic認証用のテスト環境変数を追加"
```

---

## Task 4: Basic認証の失敗テストを書く（TDD赤フェーズ）

**Files:**
- Create: `tests/test_auth.py`

- [ ] **Step 1: 認証テストを書く**

`tests/test_auth.py` を作成：

```python
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
```

- [ ] **Step 2: 赤フェーズ確認**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && pytest tests/test_auth.py -v`
Expected: `test_index_without_auth_returns_401`・`test_index_with_invalid_auth_returns_401`・`test_fetch_without_auth_returns_401`・`test_upload_without_auth_returns_401` が全てFAIL（まだ認証未実装なので200が返る）。`test_index_with_valid_auth_returns_200` はPASS（既に200を返すため）。

---

## Task 5: `app/__init__.py` にBasic認証を実装（TDD緑フェーズ）

**Files:**
- Modify: `app/__init__.py`

- [ ] **Step 1: 認証を実装**

`app/__init__.py` を以下の内容に置き換え：

```python
from flask import Flask
from flask_httpauth import HTTPBasicAuth

from app.config import Config

auth = HTTPBasicAuth()


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(Config)

    @auth.verify_password
    def verify_password(username, password):
        if (
            username == app.config["BASIC_AUTH_USERNAME"]
            and password == app.config["BASIC_AUTH_PASSWORD"]
        ):
            return username
        return None

    from app.routes import bp

    @bp.before_request
    @auth.login_required
    def require_auth():
        pass

    app.register_blueprint(bp, url_prefix=app.config["URL_PREFIX"])

    return app
```

- [ ] **Step 2: 認証テストが通ることを確認**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && pytest tests/test_auth.py -v`
Expected: 全5テストがPASS

- [ ] **Step 3: Commit（既存テストは次のタスクで修正するので、まだコミットしない…ではなく、ここでコミットしてOK）**

```bash
git add app/__init__.py
git commit -m "feat: 全ルートにBasic認証を適用"
```

---

## Task 6: 既存テストに認証ヘッダを追加

**Files:**
- Modify: `tests/test_routes.py`

**理由:** Task 5 で全ルートに認証が適用されたため、`test_routes.py` の全リクエストが401で失敗する。認証ヘッダを付与する。

- [ ] **Step 1: 既存テストが壊れていることを確認**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && pytest tests/test_routes.py -v`
Expected: 全テストが401でFAIL

- [ ] **Step 2: `tests/test_routes.py` を修正**

先頭のimportに追加：

```python
import base64
```

`client` fixture の後に認証ヘッダヘルパーとオートユース fixture を追加：

```python
@pytest.fixture(autouse=True)
def auth_headers(client):
    """全てのテストリクエストにBasic認証ヘッダを自動付与する。"""
    token = base64.b64encode(b"testuser:testpass").decode()
    client.environ_base["HTTP_AUTHORIZATION"] = f"Basic {token}"
    return client
```

変更後の `tests/test_routes.py` の完全な内容：

```python
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
```

- [ ] **Step 3: テストが全てPASSすることを確認**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && pytest tests/ -v`
Expected: 全テストPASS（`test_routes.py` + `test_auth.py` + `test_scraper.py` + `test_wordpress.py`）

- [ ] **Step 4: Commit**

```bash
git add tests/test_routes.py tests/test_auth.py
git commit -m "test: Basic認証対応のテストを追加・既存テストを更新"
```

---

## Task 7: `render.yaml` に環境変数を追加

**Files:**
- Modify: `render.yaml`

- [ ] **Step 1: `envVars` セクションに追加**

`render.yaml` の `envVars:` の末尾（`GBP_SEARCH_URL` の後）に以下を追加：

```yaml
      - key: BASIC_AUTH_USERNAME
        sync: false
      - key: BASIC_AUTH_PASSWORD
        sync: false
```

変更後の完全な `render.yaml`：

```yaml
services:
  - type: web
    name: gold-price-uploader
    runtime: docker
    plan: free
    envVars:
      - key: FLASK_SECRET_KEY
        generateValue: true
      - key: APP_URL_PREFIX
        value: /gold
      - key: WP_SITE_URL
        sync: false
      - key: WP_USERNAME
        sync: false
      - key: WP_APP_PASSWORD
        sync: false
      - key: WP_PAGE_ID
        sync: false
      - key: GOLD_SOURCE_URL
        value: https://www.net-japan.co.jp/precious_metal_partner/
      - key: GBP_SEARCH_URL
        value: https://www.google.com/search?q=フリマハイクラス
      - key: BASIC_AUTH_USERNAME
        sync: false
      - key: BASIC_AUTH_PASSWORD
        sync: false
```

- [ ] **Step 2: Commit**

```bash
git add render.yaml
git commit -m "feat: Render環境変数にBasic認証の設定を追加"
```

---

## Task 8: ローカル動作確認

**Files:** なし（手動確認）

- [ ] **Step 1: `.env` にテスト用の認証情報を追加**

`.env` ファイル（ローカル開発用、git管理外）に以下を追加：

```
BASIC_AUTH_USERNAME=kayaki-obi_-1
BASIC_AUTH_PASSWORD=d,5c@NW2=eb(
```

- [ ] **Step 2: ローカルサーバー起動**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && python wsgi.py`（または gunicorn）

- [ ] **Step 3: ブラウザで `http://localhost:5000/gold/` にアクセス**

Expected: Basic認証ダイアログが表示される。`kayaki-obi_-1` / `d,5c@NW2=eb(` で通過、違う値で401。

- [ ] **Step 4: 全テストを再実行**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && pytest tests/ -v`
Expected: 全テストPASS

---

## Task 9: Render本番反映手順（ユーザーが実施）

**Files:** なし（Render ダッシュボード操作）

- [ ] **Step 1: コード変更をpush**

```bash
git push origin main
```

- [ ] **Step 2: Render ダッシュボードで環境変数を設定**

1. https://dashboard.render.com/ を開く
2. サービス `kinprice` を選択
3. **Environment** タブ → **Add Environment Variable**
4. 以下を追加：
   - `BASIC_AUTH_USERNAME`: `kayaki-obi_-1`
   - `BASIC_AUTH_PASSWORD`: `d,5c@NW2=eb(`
5. **Save Changes** → 自動デプロイ開始

- [ ] **Step 3: 本番動作確認**

1. デプロイ完了後、https://kinprice.onrender.com/gold/ を開く
2. Basic認証ダイアログが表示されることを確認
3. `kayaki-obi_-1` / `d,5c@NW2=eb(` で通過することを確認
4. 誤った認証情報で401が返ることを確認
