# 金価格アップロードツール 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 田中貴金属から金価格を取得し、確認・修正後にWordPress固定ページとGoogleビジネスプロフィールに投稿するWebツールを構築する。

**Architecture:** Flask Webアプリで、スクレイピング・WordPress API・Google Business Profile APIの3つの機能をエンドポイントとして提供。Nginx + Basic認証 + HTTPSでセキュリティを確保し、VPS上にデプロイする。

**Tech Stack:** Python 3.11+, Flask, requests, BeautifulSoup4, google-auth, google-api-python-client, Gunicorn, Nginx

---

## ファイル構成

```
gold-price-uploader/
├── app/
│   ├── __init__.py          # Flaskアプリファクトリ
│   ├── config.py            # 設定管理（環境変数読み込み）
│   ├── scraper.py           # 田中貴金属スクレイピング
│   ├── wordpress.py         # WordPress API連携
│   ├── google_business.py   # Google Business Profile API連携
│   └── routes.py            # ルーティング（画面・API）
├── templates/
│   └── index.html           # 操作画面テンプレート
├── static/
│   └── style.css            # スタイルシート
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py      # スクレイピングテスト
│   ├── test_wordpress.py    # WordPress APIテスト
│   ├── test_google_business.py  # Google API テスト
│   └── test_routes.py       # ルーティングテスト
├── deploy/
│   ├── nginx.conf           # Nginx設定テンプレート
│   ├── gold-uploader.service # systemdユニットファイル
│   └── setup.sh             # サーバー初期セットアップスクリプト
├── .env.example             # 環境変数テンプレート
├── .gitignore
├── requirements.txt
└── wsgi.py                  # Gunicornエントリポイント
```

---

## Task 1: プロジェクト初期セットアップ

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/config.py`

- [ ] **Step 1: gitリポジトリを初期化**

```bash
cd /Users/atsushishibazaki/Desktop/googlenews
git init
```

- [ ] **Step 2: requirements.txt を作成**

```txt
Flask==3.1.0
requests==2.32.3
beautifulsoup4==4.13.3
python-dotenv==1.1.0
google-auth==2.38.0
google-auth-oauthlib==1.2.1
google-api-python-client==2.164.0
gunicorn==23.0.0
pytest==8.3.5
```

- [ ] **Step 3: .gitignore を作成**

```
__pycache__/
*.pyc
.env
venv/
.pytest_cache/
```

- [ ] **Step 4: .env.example を作成**

```bash
# Flask
FLASK_SECRET_KEY=change-this-to-random-string
APP_URL_PREFIX=/your-random-path-here

# WordPress
WP_SITE_URL=https://example.com
WP_USERNAME=admin
WP_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
WP_PAGE_ID=123

# Google Business Profile
GOOGLE_ACCOUNT_ID=accounts/123456789
GOOGLE_LOCATION_ID=locations/123456789
GOOGLE_CREDENTIALS_PATH=./google-credentials.json

# スクレイピング
GOLD_SOURCE_URL=https://gold.tanaka.co.jp/commodity/souba/d-gold.php
```

- [ ] **Step 5: app/config.py を作成**

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

    # Google Business Profile
    GOOGLE_ACCOUNT_ID = os.environ["GOOGLE_ACCOUNT_ID"]
    GOOGLE_LOCATION_ID = os.environ["GOOGLE_LOCATION_ID"]
    GOOGLE_CREDENTIALS_PATH = os.environ.get(
        "GOOGLE_CREDENTIALS_PATH", "./google-credentials.json"
    )

    # スクレイピング
    GOLD_SOURCE_URL = os.environ.get(
        "GOLD_SOURCE_URL",
        "https://gold.tanaka.co.jp/commodity/souba/d-gold.php",
    )
```

- [ ] **Step 6: app/__init__.py を作成**

```python
from flask import Flask
from app.config import Config


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(Config)

    from app.routes import bp

    app.register_blueprint(bp, url_prefix=app.config["URL_PREFIX"])

    return app
```

- [ ] **Step 7: Python仮想環境を作成し依存関係をインストール**

```bash
cd /Users/atsushishibazaki/Desktop/googlenews
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 8: コミット**

```bash
git add requirements.txt .gitignore .env.example app/__init__.py app/config.py
git commit -m "feat: プロジェクト初期セットアップ"
```

---

## Task 2: 金価格スクレイピング

**Files:**
- Create: `app/scraper.py`
- Create: `tests/test_scraper.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: テスト用の固定HTMLを用意し、テストを書く**

```python
# tests/__init__.py
```

```python
# tests/test_scraper.py
from app.scraper import scrape_gold_price

SAMPLE_HTML = """
<html>
<body>
<table>
<tr><th>店頭小売価格(税込)</th><td>14,589円</td></tr>
<tr><th>店頭買取価格(税込)</th><td>14,200円</td></tr>
</table>
</body>
</html>
"""


def test_scrape_gold_price_parses_prices():
    """固定HTMLから小売・買取価格を正しく抽出できる"""
    result = scrape_gold_price(html=SAMPLE_HTML)
    assert result["retail_price"] == "14,589"
    assert result["purchase_price"] == "14,200"


def test_scrape_gold_price_includes_date():
    """結果に日付が含まれる"""
    result = scrape_gold_price(html=SAMPLE_HTML)
    assert "date" in result
```

- [ ] **Step 2: テストを実行して失敗を確認**

```bash
cd /Users/atsushishibazaki/Desktop/googlenews
source venv/bin/activate
pytest tests/test_scraper.py -v
```

Expected: FAIL（`scraper`モジュールが存在しない）

- [ ] **Step 3: スクレイパーを実装**

```python
# app/scraper.py
from datetime import date

import requests
from bs4 import BeautifulSoup


def scrape_gold_price(url: str | None = None, html: str | None = None) -> dict:
    """田中貴金属のサイトから金価格を取得する。

    Args:
        url: スクレイピング先URL。htmlが指定されている場合は無視。
        html: テスト用にHTMLを直接渡す場合に使用。

    Returns:
        dict: retail_price, purchase_price, date を含む辞書
    """
    if html is None:
        if url is None:
            raise ValueError("url or html must be provided")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        html = response.text

    soup = BeautifulSoup(html, "html.parser")

    retail_price = None
    purchase_price = None

    # テーブルの行から価格を探す
    for row in soup.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if th and td:
            header_text = th.get_text(strip=True)
            value_text = td.get_text(strip=True)
            # 「円」や余計な文字を除去し、カンマ付き数値を抽出
            price = value_text.replace("円", "").strip()
            if "小売" in header_text:
                retail_price = price
            elif "買取" in header_text:
                purchase_price = price

    if retail_price is None or purchase_price is None:
        raise ValueError(
            "金価格の取得に失敗しました。ページ構造が変更された可能性があります。"
        )

    return {
        "retail_price": retail_price,
        "purchase_price": purchase_price,
        "date": date.today().isoformat(),
    }
```

- [ ] **Step 4: テストを実行して成功を確認**

```bash
pytest tests/test_scraper.py -v
```

Expected: PASS

- [ ] **Step 5: 実際のサイトからの取得テスト（手動確認）**

```bash
python3 -c "
from app.scraper import scrape_gold_price
result = scrape_gold_price(url='https://gold.tanaka.co.jp/commodity/souba/d-gold.php')
print(result)
"
```

※ 実際のHTML構造に合わせてパース処理を調整する可能性あり

- [ ] **Step 6: コミット**

```bash
git add app/scraper.py tests/__init__.py tests/test_scraper.py
git commit -m "feat: 田中貴金属から金価格をスクレイピングする機能を追加"
```

---

## Task 3: WordPress API連携

**Files:**
- Create: `app/wordpress.py`
- Create: `tests/test_wordpress.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_wordpress.py
from unittest.mock import patch, MagicMock
from app.wordpress import update_gold_page


def test_update_gold_page_sends_correct_request():
    """WordPress APIに正しいリクエストを送信する"""
    with patch("app.wordpress.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "link": "https://example.com/gold"}
        mock_post.return_value = mock_response

        result = update_gold_page(
            site_url="https://example.com",
            username="admin",
            app_password="test-pass",
            page_id=123,
            retail_price="14,589",
            purchase_price="14,200",
            price_date="2026-04-02",
        )

        assert result["success"] is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/wp-json/wp/v2/pages/123" in call_args[0][0]


def test_update_gold_page_handles_api_error():
    """WordPress APIエラー時にエラー情報を返す"""
    with patch("app.wordpress.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")
        mock_post.return_value = mock_response

        result = update_gold_page(
            site_url="https://example.com",
            username="admin",
            app_password="wrong-pass",
            page_id=123,
            retail_price="14,589",
            purchase_price="14,200",
            price_date="2026-04-02",
        )

        assert result["success"] is False
        assert "error" in result
```

- [ ] **Step 2: テストを実行して失敗を確認**

```bash
pytest tests/test_wordpress.py -v
```

Expected: FAIL

- [ ] **Step 3: WordPress API連携を実装**

```python
# app/wordpress.py
import requests
from requests.auth import HTTPBasicAuth


def update_gold_page(
    site_url: str,
    username: str,
    app_password: str,
    page_id: int,
    retail_price: str,
    purchase_price: str,
    price_date: str,
) -> dict:
    """WordPressの固定ページを金価格で更新する。

    Args:
        site_url: WordPressサイトのURL（例: https://example.com）
        username: WordPressユーザー名
        app_password: WordPressアプリケーションパスワード
        page_id: 更新対象の固定ページID
        retail_price: 小売価格（カンマ付き文字列）
        purchase_price: 買取価格（カンマ付き文字列）
        price_date: 日付文字列（YYYY-MM-DD）

    Returns:
        dict: success, message, link を含む辞書
    """
    content = _build_page_content(retail_price, purchase_price, price_date)

    api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}"

    try:
        response = requests.post(
            api_url,
            json={"content": content},
            auth=HTTPBasicAuth(username, app_password),
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "message": "WordPressの固定ページを更新しました",
            "link": data.get("link", ""),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"WordPress更新エラー: {str(e)}",
        }


def _build_page_content(
    retail_price: str, purchase_price: str, price_date: str
) -> str:
    """固定ページ用のHTMLコンテンツを生成する。"""
    return f"""
<div class="gold-price-container">
  <p class="gold-price-date">{price_date} 現在</p>
  <table class="gold-price-table">
    <tr>
      <th>金小売価格（税込）</th>
      <td>{retail_price} 円/g</td>
    </tr>
    <tr>
      <th>金買取価格（税込）</th>
      <td>{purchase_price} 円/g</td>
    </tr>
  </table>
</div>
"""
```

- [ ] **Step 4: テストを実行して成功を確認**

```bash
pytest tests/test_wordpress.py -v
```

Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add app/wordpress.py tests/test_wordpress.py
git commit -m "feat: WordPress固定ページ更新機能を追加"
```

---

## Task 4: Google Business Profile API連携

**Files:**
- Create: `app/google_business.py`
- Create: `tests/test_google_business.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_google_business.py
from unittest.mock import patch, MagicMock
from app.google_business import create_post, delete_todays_posts


def test_create_post_sends_correct_request():
    """Google Business Profile APIに正しいリクエストを送信する"""
    mock_service = MagicMock()
    mock_create = mock_service.accounts().locations().localPosts().create
    mock_create.return_value.execute.return_value = {"name": "accounts/123/locations/456/localPosts/789"}

    result = create_post(
        service=mock_service,
        account_id="accounts/123",
        location_id="locations/456",
        retail_price="14,589",
        purchase_price="14,200",
        price_date="2026-04-02",
    )

    assert result["success"] is True
    mock_create.assert_called_once()


def test_create_post_handles_api_error():
    """Google APIエラー時にエラー情報を返す"""
    mock_service = MagicMock()
    mock_create = mock_service.accounts().locations().localPosts().create
    mock_create.return_value.execute.side_effect = Exception("API Error")

    result = create_post(
        service=mock_service,
        account_id="accounts/123",
        location_id="locations/456",
        retail_price="14,589",
        purchase_price="14,200",
        price_date="2026-04-02",
    )

    assert result["success"] is False
    assert "error" in result
```

- [ ] **Step 2: テストを実行して失敗を確認**

```bash
pytest tests/test_google_business.py -v
```

Expected: FAIL

- [ ] **Step 3: Google Business Profile API連携を実装**

```python
# app/google_business.py
from datetime import date, datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/business.manage"]


def get_service(credentials_path: str):
    """Google Business Profile APIのサービスオブジェクトを取得する。"""
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    return build("mybusinessbusinessinformation", "v1", credentials=credentials)


def create_post(
    service,
    account_id: str,
    location_id: str,
    retail_price: str,
    purchase_price: str,
    price_date: str,
) -> dict:
    """Googleビジネスプロフィールに金価格の投稿を作成する。

    Args:
        service: Google APIサービスオブジェクト
        account_id: GoogleアカウントID（例: accounts/123456789）
        location_id: ロケーションID（例: locations/123456789）
        retail_price: 小売価格（カンマ付き文字列）
        purchase_price: 買取価格（カンマ付き文字列）
        price_date: 日付文字列（YYYY-MM-DD）

    Returns:
        dict: success, message を含む辞書
    """
    summary = (
        f"【{price_date} 金価格】\n"
        f"小売価格: {retail_price} 円/g\n"
        f"買取価格: {purchase_price} 円/g"
    )

    post_body = {
        "languageCode": "ja",
        "summary": summary,
        "topicType": "STANDARD",
    }

    parent = f"{account_id}/{location_id}"

    try:
        result = (
            service.accounts()
            .locations()
            .localPosts()
            .create(parent=parent, body=post_body)
            .execute()
        )
        return {
            "success": True,
            "message": "Googleビジネスプロフィールに投稿しました",
            "post_name": result.get("name", ""),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Google投稿エラー: {str(e)}",
        }


def delete_todays_posts(
    service,
    account_id: str,
    location_id: str,
) -> int:
    """当日の投稿を全て削除する。

    Returns:
        int: 削除した投稿数
    """
    parent = f"{account_id}/{location_id}"
    today_str = date.today().isoformat()
    deleted_count = 0

    try:
        response = (
            service.accounts()
            .locations()
            .localPosts()
            .list(parent=parent)
            .execute()
        )
        posts = response.get("localPosts", [])

        for post in posts:
            create_time = post.get("createTime", "")
            if create_time.startswith(today_str):
                post_name = post["name"]
                service.accounts().locations().localPosts().delete(
                    name=post_name
                ).execute()
                deleted_count += 1

    except Exception:
        pass

    return deleted_count
```

**注意:** Google Business Profile APIの正確なエンドポイントは、実際のAPI設定時に確認・調整が必要。Google My Business APIは2024年以降にBusiness Profile APIへ移行しており、認証方式（サービスアカウント vs OAuth2）もアカウントの種類により異なる。Task実行時に最新のAPIドキュメントを確認すること。

- [ ] **Step 4: テストを実行して成功を確認**

```bash
pytest tests/test_google_business.py -v
```

Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add app/google_business.py tests/test_google_business.py
git commit -m "feat: Googleビジネスプロフィール投稿機能を追加"
```

---

## Task 5: Flaskルーティングと操作画面

**Files:**
- Create: `app/routes.py`
- Create: `templates/index.html`
- Create: `static/style.css`
- Create: `tests/test_routes.py`
- Create: `wsgi.py`

- [ ] **Step 1: ルーティングのテストを書く**

```python
# tests/test_routes.py
import os
import pytest

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ.setdefault("WP_SITE_URL", "https://example.com")
os.environ.setdefault("WP_USERNAME", "admin")
os.environ.setdefault("WP_APP_PASSWORD", "test-pass")
os.environ.setdefault("WP_PAGE_ID", "123")
os.environ.setdefault("GOOGLE_ACCOUNT_ID", "accounts/123")
os.environ.setdefault("GOOGLE_LOCATION_ID", "locations/456")

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_page_returns_200(client):
    """操作画面が正常に表示される"""
    prefix = client.application.config["URL_PREFIX"]
    response = client.get(f"{prefix}/")
    assert response.status_code == 200
    assert "金価格" in response.data.decode("utf-8")


def test_fetch_endpoint_returns_json(client):
    """fetchエンドポイントがJSONを返す"""
    prefix = client.application.config["URL_PREFIX"]
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "app.routes.scrape_gold_price",
            lambda url: {
                "retail_price": "14,589",
                "purchase_price": "14,200",
                "date": "2026-04-02",
            },
        )
        response = client.post(f"{prefix}/fetch")
        assert response.status_code == 200
        data = response.get_json()
        assert data["retail_price"] == "14,589"
```

- [ ] **Step 2: テストを実行して失敗を確認**

```bash
pytest tests/test_routes.py -v
```

Expected: FAIL

- [ ] **Step 3: ルーティングを実装**

```python
# app/routes.py
import re

from flask import Blueprint, current_app, jsonify, render_template, request

from app.scraper import scrape_gold_price
from app.wordpress import update_gold_page
from app.google_business import get_service, create_post, delete_todays_posts

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """操作画面を表示する。"""
    return render_template("index.html")


@bp.route("/fetch", methods=["POST"])
def fetch_price():
    """田中貴金属から金価格を取得して返す。"""
    try:
        url = current_app.config["GOLD_SOURCE_URL"]
        result = scrape_gold_price(url=url)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/upload", methods=["POST"])
def upload_price():
    """金価格をWordPressとGoogleビジネスに投稿する。"""
    data = request.get_json()

    retail_price = data.get("retail_price", "")
    purchase_price = data.get("purchase_price", "")
    price_date = data.get("date", "")
    post_to_wp = data.get("post_to_wp", True)
    post_to_google = data.get("post_to_google", True)

    # 入力バリデーション: カンマ付き数値のみ許可
    price_pattern = re.compile(r"^[\d,]+$")
    if not price_pattern.match(retail_price) or not price_pattern.match(purchase_price):
        return jsonify({"error": "価格は数値のみ入力してください"}), 400

    results = {}

    if post_to_wp:
        wp_result = update_gold_page(
            site_url=current_app.config["WP_SITE_URL"],
            username=current_app.config["WP_USERNAME"],
            app_password=current_app.config["WP_APP_PASSWORD"],
            page_id=current_app.config["WP_PAGE_ID"],
            retail_price=retail_price,
            purchase_price=purchase_price,
            price_date=price_date,
        )
        results["wordpress"] = wp_result

    if post_to_google:
        try:
            service = get_service(current_app.config["GOOGLE_CREDENTIALS_PATH"])
            account_id = current_app.config["GOOGLE_ACCOUNT_ID"]
            location_id = current_app.config["GOOGLE_LOCATION_ID"]

            # 当日の既存投稿を削除
            deleted = delete_todays_posts(service, account_id, location_id)

            # 新規投稿
            google_result = create_post(
                service=service,
                account_id=account_id,
                location_id=location_id,
                retail_price=retail_price,
                purchase_price=purchase_price,
                price_date=price_date,
            )
            if deleted > 0:
                google_result["message"] += f"（既存{deleted}件を上書き）"
            results["google"] = google_result
        except Exception as e:
            results["google"] = {
                "success": False,
                "error": f"Google投稿エラー: {str(e)}",
            }

    return jsonify(results)
```

- [ ] **Step 4: HTMLテンプレートを作成**

```html
<!-- templates/index.html -->
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>金価格アップロードツール</title>
    <link rel="stylesheet" href="{{ url_for('main.static', filename='style.css') }}">
</head>
<body>
    <div class="container">
        <h1>金価格アップロードツール</h1>

        <button id="fetch-btn" class="btn btn-fetch">価格を取得する</button>

        <div id="price-form" class="price-form" style="display: none;">
            <div class="form-group">
                <label for="retail-price">金小売価格（税込）</label>
                <div class="input-wrapper">
                    <input type="text" id="retail-price" class="price-input" pattern="[\d,]+" required>
                    <span class="unit">円/g</span>
                </div>
            </div>

            <div class="form-group">
                <label for="purchase-price">金買取価格（税込）</label>
                <div class="input-wrapper">
                    <input type="text" id="purchase-price" class="price-input" pattern="[\d,]+" required>
                    <span class="unit">円/g</span>
                </div>
            </div>

            <div class="form-group">
                <label for="price-date">日付</label>
                <input type="text" id="price-date" class="date-input" readonly>
            </div>

            <div class="checkbox-group">
                <label>
                    <input type="checkbox" id="post-wp" checked>
                    WordPressに投稿
                </label>
                <label>
                    <input type="checkbox" id="post-google" checked>
                    Googleビジネスに投稿
                </label>
            </div>

            <button id="upload-btn" class="btn btn-upload">アップロード</button>
        </div>

        <div id="status" class="status"></div>
    </div>

    <script>
        const PREFIX = "{{ request.script_root }}{{ request.url_rule.rule.rsplit('/', 1)[0] }}";

        document.getElementById("fetch-btn").addEventListener("click", async () => {
            const btn = document.getElementById("fetch-btn");
            btn.disabled = true;
            btn.textContent = "取得中...";
            document.getElementById("status").textContent = "";

            try {
                const res = await fetch(PREFIX + "/fetch", { method: "POST" });
                const data = await res.json();

                if (data.error) {
                    document.getElementById("status").textContent = "エラー: " + data.error;
                    document.getElementById("status").className = "status error";
                    return;
                }

                document.getElementById("retail-price").value = data.retail_price;
                document.getElementById("purchase-price").value = data.purchase_price;
                document.getElementById("price-date").value = data.date;
                document.getElementById("price-form").style.display = "block";
            } catch (e) {
                document.getElementById("status").textContent = "取得に失敗しました";
                document.getElementById("status").className = "status error";
            } finally {
                btn.disabled = false;
                btn.textContent = "価格を取得する";
            }
        });

        document.getElementById("upload-btn").addEventListener("click", async () => {
            const btn = document.getElementById("upload-btn");
            btn.disabled = true;
            btn.textContent = "アップロード中...";
            document.getElementById("status").textContent = "";

            const body = {
                retail_price: document.getElementById("retail-price").value,
                purchase_price: document.getElementById("purchase-price").value,
                date: document.getElementById("price-date").value,
                post_to_wp: document.getElementById("post-wp").checked,
                post_to_google: document.getElementById("post-google").checked,
            };

            try {
                const res = await fetch(PREFIX + "/upload", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(body),
                });
                const data = await res.json();

                let messages = [];
                if (data.wordpress) {
                    messages.push(data.wordpress.success
                        ? "WordPress: 更新完了"
                        : "WordPress: " + data.wordpress.error);
                }
                if (data.google) {
                    messages.push(data.google.success
                        ? "Google: " + data.google.message
                        : "Google: " + data.google.error);
                }

                const allSuccess = (!data.wordpress || data.wordpress.success)
                    && (!data.google || data.google.success);

                document.getElementById("status").textContent = messages.join("\n");
                document.getElementById("status").className =
                    "status " + (allSuccess ? "success" : "error");
            } catch (e) {
                document.getElementById("status").textContent = "アップロードに失敗しました";
                document.getElementById("status").className = "status error";
            } finally {
                btn.disabled = false;
                btn.textContent = "アップロード";
            }
        });
    </script>
</body>
</html>
```

- [ ] **Step 5: CSSを作成**

```css
/* static/style.css */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif;
    background: #f5f5f5;
    color: #333;
    padding: 2rem;
}

.container {
    max-width: 480px;
    margin: 0 auto;
    background: #fff;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

h1 {
    font-size: 1.4rem;
    margin-bottom: 1.5rem;
    text-align: center;
    color: #1a1a1a;
}

.btn {
    display: block;
    width: 100%;
    padding: 0.8rem;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: bold;
    cursor: pointer;
    transition: opacity 0.2s;
}

.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-fetch {
    background: #4a90d9;
    color: #fff;
}

.btn-upload {
    background: #e8963e;
    color: #fff;
    margin-top: 1rem;
}

.price-form {
    margin-top: 1.5rem;
}

.form-group {
    margin-bottom: 1rem;
}

.form-group label {
    display: block;
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 0.3rem;
}

.input-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.price-input {
    flex: 1;
    padding: 0.6rem;
    font-size: 1.2rem;
    font-weight: bold;
    border: 2px solid #ddd;
    border-radius: 6px;
    text-align: right;
}

.price-input:focus {
    border-color: #4a90d9;
    outline: none;
}

.unit {
    font-size: 0.9rem;
    color: #666;
    white-space: nowrap;
}

.date-input {
    width: 100%;
    padding: 0.6rem;
    font-size: 1rem;
    border: 2px solid #ddd;
    border-radius: 6px;
    background: #f9f9f9;
}

.checkbox-group {
    margin-top: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.checkbox-group label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.95rem;
    cursor: pointer;
}

.status {
    margin-top: 1.5rem;
    padding: 1rem;
    border-radius: 8px;
    font-size: 0.9rem;
    white-space: pre-line;
    display: none;
}

.status:not(:empty) {
    display: block;
}

.status.success {
    background: #e8f5e9;
    color: #2e7d32;
}

.status.error {
    background: #ffeef0;
    color: #c62828;
}
```

- [ ] **Step 6: wsgi.py を作成**

```python
# wsgi.py
from app import create_app

app = create_app()
```

- [ ] **Step 7: テストを実行して成功を確認**

```bash
pytest tests/test_routes.py -v
```

Expected: PASS

- [ ] **Step 8: ローカルで動作確認**

```bash
# .env ファイルを作成（テスト用の値で）
cp .env.example .env
# FLASK_SECRET_KEY を適当な値に変更

# 開発サーバー起動
FLASK_APP=wsgi.py flask run --port 5000
```

ブラウザで `http://localhost:5000/your-random-path-here/` にアクセスして画面が表示されることを確認。

- [ ] **Step 9: コミット**

```bash
git add app/routes.py templates/index.html static/style.css wsgi.py tests/test_routes.py
git commit -m "feat: 操作画面とルーティングを追加"
```

---

## Task 6: デプロイ設定ファイル

**Files:**
- Create: `deploy/nginx.conf`
- Create: `deploy/gold-uploader.service`
- Create: `deploy/setup.sh`

- [ ] **Step 1: Nginx設定テンプレートを作成**

```nginx
# deploy/nginx.conf
# /etc/nginx/sites-available/gold-uploader として配置

server {
    listen 80;
    server_name YOUR_DOMAIN;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name YOUR_DOMAIN;

    ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;

    # セキュリティヘッダー
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Basic認証
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- [ ] **Step 2: systemdユニットファイルを作成**

```ini
# deploy/gold-uploader.service
# /etc/systemd/system/gold-uploader.service として配置

[Unit]
Description=Gold Price Uploader Flask App
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/gold-price-uploader
Environment="PATH=/opt/gold-price-uploader/venv/bin"
EnvironmentFile=/opt/gold-price-uploader/.env
ExecStart=/opt/gold-price-uploader/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    --timeout 30 \
    wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: セットアップスクリプトを作成**

```bash
#!/bin/bash
# deploy/setup.sh
# VPSの初期セットアップスクリプト
# 使い方: sudo bash setup.sh YOUR_DOMAIN

set -euo pipefail

DOMAIN="${1:?ドメインを指定してください（例: gold.example.com）}"
APP_DIR="/opt/gold-price-uploader"

echo "=== システムアップデート ==="
apt update && apt upgrade -y

echo "=== 必要パッケージのインストール ==="
apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx ufw

echo "=== ファイアウォール設定 ==="
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "=== unattended-upgrades設定 ==="
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

echo "=== アプリケーションディレクトリ作成 ==="
mkdir -p "$APP_DIR"
cp -r . "$APP_DIR/"

echo "=== Python仮想環境セットアップ ==="
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "=== .envファイル確認 ==="
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "WARNING: .envファイルを編集してください: $APP_DIR/.env"
fi

echo "=== Basic認証ユーザー作成 ==="
echo "Basic認証のパスワードを入力してください:"
htpasswd -c /etc/nginx/.htpasswd goldadmin

echo "=== Nginx設定 ==="
cp deploy/nginx.conf /etc/nginx/sites-available/gold-uploader
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" /etc/nginx/sites-available/gold-uploader
ln -sf /etc/nginx/sites-available/gold-uploader /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "=== SSL証明書取得 ==="
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN"

echo "=== systemdサービス設定 ==="
cp deploy/gold-uploader.service /etc/systemd/system/
chown -R www-data:www-data "$APP_DIR"
systemctl daemon-reload
systemctl enable gold-uploader
systemctl start gold-uploader

echo "=== セットアップ完了 ==="
echo "サイト: https://$DOMAIN"
echo ""
echo "次のステップ:"
echo "1. .envファイルを編集: $APP_DIR/.env"
echo "2. サービス再起動: systemctl restart gold-uploader"
echo "3. SSHパスワードログインを無効化: /etc/ssh/sshd_config で PasswordAuthentication no"
```

- [ ] **Step 4: コミット**

```bash
git add deploy/nginx.conf deploy/gold-uploader.service deploy/setup.sh
chmod +x deploy/setup.sh
git commit -m "feat: デプロイ設定ファイルを追加（Nginx, systemd, セットアップスクリプト）"
```

---

## Task 7: 全体結合テストとスクレイピング調整

**Files:**
- Modify: `app/scraper.py`（実際のHTML構造に合わせて調整）
- Modify: `tests/test_scraper.py`（実際のHTMLでテスト追加）

- [ ] **Step 1: 実際の田中貴金属サイトにアクセスしてHTML構造を確認**

```bash
python3 -c "
import requests
from bs4 import BeautifulSoup
r = requests.get('https://gold.tanaka.co.jp/commodity/souba/d-gold.php')
soup = BeautifulSoup(r.text, 'html.parser')
# テーブルの構造を確認
for table in soup.find_all('table'):
    print('--- TABLE ---')
    for row in table.find_all('tr'):
        cells = [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]
        print(cells)
    print()
"
```

- [ ] **Step 2: 実際の構造に合わせてscraper.pyを調整**

Step 1の結果に基づいてパース処理を修正する。実際のHTML構造はサイト訪問時に確定する。

- [ ] **Step 3: テストを更新して実行**

```bash
pytest tests/ -v
```

Expected: ALL PASS

- [ ] **Step 4: エンドツーエンドの手動テスト**

```bash
FLASK_APP=wsgi.py flask run --port 5000
```

ブラウザで以下を確認:
1. 「価格を取得する」→ 価格が表示される
2. 価格を修正できる
3. 「アップロード」→ 結果が表示される（WordPress/Googleは認証情報設定後に確認）

- [ ] **Step 5: コミット**

```bash
git add -u
git commit -m "fix: 実際のHTML構造に合わせてスクレイパーを調整"
```

---

## 実装上の注意事項

### Google Business Profile API について
- Google Business Profile APIは2024年以降に大幅改訂されている。実装時に最新のAPIドキュメント（https://developers.google.com/my-business/reference/rest）を確認し、エンドポイントや認証方式を調整すること。
- サービスアカウントでの認証が使えない場合はOAuth2フロー（ユーザー同意画面あり）に切り替える必要がある。

### スクレイピングの安定性
- 田中貴金属のサイト構造が変わった場合にスクレイパーが壊れる可能性がある。エラーメッセージで「ページ構造が変更された可能性があります」と表示して、手動確認を促す設計にしている。

### WordPress Application Password
- WordPress 5.6以降で利用可能。管理画面 → ユーザー → アプリケーションパスワードで発行する。
