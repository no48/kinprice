# 金価格アップロードツール簡素化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** スクレイピングとGoogle API投稿を削除し、手入力＋WordPress自動投稿＋GBPコピー方式にする

**Architecture:** Flask app with 2 endpoints (GET `/`, POST `/upload`). Upload posts to WordPress via REST API, returns GBP text for clipboard copy. No Playwright, no Google API.

**Tech Stack:** Flask 3.1.0, requests, python-dotenv, gunicorn, pytest

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `app/config.py` | Remove Google/scraping config, add GBP_SEARCH_URL |
| Modify | `app/routes.py` | Remove /fetch, remove Google posting, add gbp_text to response |
| Keep | `app/wordpress.py` | No changes |
| Modify | `app/__init__.py` | No changes needed (imports are in routes.py) |
| Delete | `app/scraper.py` | No longer needed |
| Delete | `app/google_business.py` | No longer needed |
| Rewrite | `templates/index.html` | Manual input form, GBP copy button |
| Modify | `static/style.css` | Add GBP result section styles |
| Modify | `tests/conftest.py` | Remove Google env vars, add GBP_SEARCH_URL |
| Rewrite | `tests/test_routes.py` | Remove fetch/Google tests, add GBP text tests |
| Delete | `tests/test_scraper.py` | No longer needed |
| Delete | `tests/test_google_business.py` | No longer needed |
| Modify | `requirements.txt` | Remove playwright, google-*, beautifulsoup4 |
| Modify | `.env` | Remove Google/scraping vars, add GBP_SEARCH_URL |
| Modify | `.env.example` | Same as .env |
| Modify | `deploy/setup.sh` | Remove Playwright install steps |
| Modify | `deploy/gold-uploader.service` | Remove PLAYWRIGHT env var |

---

### Task 1: Delete unused files and clean dependencies

**Files:**
- Delete: `app/scraper.py`
- Delete: `app/google_business.py`
- Delete: `tests/test_scraper.py`
- Delete: `tests/test_google_business.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Delete files**

```bash
rm app/scraper.py app/google_business.py tests/test_scraper.py tests/test_google_business.py
```

- [ ] **Step 2: Update requirements.txt**

Replace contents with:

```
Flask==3.1.0
requests==2.32.3
python-dotenv==1.1.0
gunicorn==23.0.0
pytest==8.3.5
```

- [ ] **Step 3: Commit**

```bash
git add -u
git add requirements.txt
git commit -m "chore: remove scraper, Google API, and unused dependencies"
```

---

### Task 2: Update config and env files

**Files:**
- Modify: `app/config.py`
- Modify: `.env`
- Modify: `.env.example`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Update app/config.py**

Replace entire file with:

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

    # GBP
    GBP_SEARCH_URL = os.environ.get(
        "GBP_SEARCH_URL",
        "https://www.google.com/search?q=フリマハイクラス",
    )
```

- [ ] **Step 2: Update .env**

Replace entire file with:

```
FLASK_SECRET_KEY=local-dev-secret-key-12345
APP_URL_PREFIX=/gold
WP_SITE_URL=https://f-high-class.jp
WP_USERNAME=f-high-class
WP_APP_PASSWORD=S1Yc t6Ut adUM WCL3 nB4r qFiO
WP_PAGE_ID=666
GBP_SEARCH_URL=https://www.google.com/search?q=フリマハイクラス
```

- [ ] **Step 3: Update .env.example**

Replace entire file with:

```
# Flask
FLASK_SECRET_KEY=change-me-in-production
APP_URL_PREFIX=/gold

# WordPress
WP_SITE_URL=https://example.com
WP_USERNAME=admin
WP_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
WP_PAGE_ID=1

# GBP (Google Business Profile)
GBP_SEARCH_URL=https://www.google.com/search?q=ビジネス名
```

- [ ] **Step 4: Update tests/conftest.py**

Replace entire file with:

```python
import os

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
os.environ.setdefault("WP_SITE_URL", "https://example.com")
os.environ.setdefault("WP_USERNAME", "admin")
os.environ.setdefault("WP_APP_PASSWORD", "xxxx-xxxx-xxxx-xxxx")
os.environ.setdefault("WP_PAGE_ID", "123")
os.environ.setdefault("GBP_SEARCH_URL", "https://www.google.com/search?q=test")
```

- [ ] **Step 5: Commit**

```bash
git add app/config.py .env .env.example tests/conftest.py
git commit -m "chore: update config - remove Google/scraping, add GBP_SEARCH_URL"
```

---

### Task 3: Rewrite routes (TDD)

**Files:**
- Rewrite: `tests/test_routes.py`
- Modify: `app/routes.py`

- [ ] **Step 1: Write new test file tests/test_routes.py**

Replace entire file with:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && source venv/bin/activate && pytest tests/test_routes.py -v`

Expected: FAIL — routes.py still imports scraper and google_business

- [ ] **Step 3: Rewrite app/routes.py**

Replace entire file with:

```python
import re
from flask import Blueprint, current_app, jsonify, render_template, request
from app.wordpress import update_gold_page

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/upload", methods=["POST"])
def upload_price():
    data = request.get_json()
    retail_price = data.get("retail_price", "")
    purchase_price = data.get("purchase_price", "")
    price_date = data.get("date", "")
    post_to_wp = data.get("post_to_wp", True)

    price_pattern = re.compile(r"^[\d,]+$")
    if not price_pattern.match(retail_price):
        return jsonify({"error": "価格は数値のみ入力してください"}), 400
    if purchase_price and not price_pattern.match(purchase_price):
        return jsonify({"error": "価格は数値のみ入力してください"}), 400
    if not purchase_price:
        purchase_price = retail_price

    date_pattern = re.compile(r"^[\d/:\s\u4e00-\u9fff]+$")
    if price_date and not date_pattern.match(price_date):
        return jsonify({"error": "日付の形式が不正です"}), 400

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

    gbp_text = f"{price_date}本日K18/1g  {purchase_price}円でお買い取りしております。"
    results["gbp_text"] = gbp_text
    results["gbp_search_url"] = current_app.config["GBP_SEARCH_URL"]

    return jsonify(results)
```

Note: date_pattern now allows Japanese characters (e.g., "4月4日") via `\u4e00-\u9fff`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_routes.py -v`

Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_routes.py app/routes.py
git commit -m "feat: simplify routes - remove scraping/Google, add GBP text"
```

---

### Task 4: Rewrite UI

**Files:**
- Rewrite: `templates/index.html`
- Modify: `static/style.css`

- [ ] **Step 1: Rewrite templates/index.html**

Replace entire file with:

```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>金価格アップロードツール</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <div class="container">
        <h1>金価格アップロードツール</h1>

        <form id="price-form" class="price-form">
            <div class="form-group">
                <label for="retail-price">小売価格</label>
                <div class="input-row">
                    <input type="text" id="retail-price" name="retail_price" placeholder="例: 26,200">
                    <span class="unit">円/g</span>
                </div>
            </div>
            <div class="form-group">
                <label for="purchase-price">買取価格</label>
                <div class="input-row">
                    <input type="text" id="purchase-price" name="purchase_price" placeholder="例: 25,000">
                    <span class="unit">円/g</span>
                </div>
            </div>
            <div class="form-group">
                <label for="price-date">日付</label>
                <input type="text" id="price-date" name="date" placeholder="例: 4月4日">
            </div>

            <button type="button" id="btn-upload" class="btn btn-upload">WordPressにアップロード</button>
        </form>

        <div id="status" class="status hidden"></div>

        <div id="gbp-section" class="gbp-section hidden">
            <h2>GBP投稿用テキスト</h2>
            <div id="gbp-text" class="gbp-text"></div>
            <button id="btn-gbp" class="btn btn-gbp">コピーしてGBPを開く</button>
        </div>
    </div>

    <script>
        const BASE_URL = "{{ url_for('main.index') }}".replace(/\/$/, '');

        const btnUpload = document.getElementById('btn-upload');
        const statusEl = document.getElementById('status');
        const retailPriceEl = document.getElementById('retail-price');
        const purchasePriceEl = document.getElementById('purchase-price');
        const priceDateEl = document.getElementById('price-date');
        const gbpSection = document.getElementById('gbp-section');
        const gbpTextEl = document.getElementById('gbp-text');
        const btnGbp = document.getElementById('btn-gbp');

        let gbpText = '';
        let gbpSearchUrl = '';

        function showStatus(message, type) {
            statusEl.textContent = message;
            statusEl.className = 'status ' + type;
            statusEl.classList.remove('hidden');
        }

        btnUpload.addEventListener('click', async () => {
            btnUpload.disabled = true;
            btnUpload.textContent = 'アップロード中...';
            statusEl.classList.add('hidden');
            gbpSection.classList.add('hidden');

            const payload = {
                retail_price: retailPriceEl.value,
                purchase_price: purchasePriceEl.value,
                date: priceDateEl.value,
                post_to_wp: true,
            };

            try {
                const res = await fetch(BASE_URL + '/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const data = await res.json();

                if (data.error) {
                    showStatus('エラー: ' + data.error, 'error');
                } else {
                    const messages = [];
                    if (data.wordpress) {
                        if (data.wordpress.success) {
                            messages.push('WordPress: ' + (data.wordpress.message || '投稿成功'));
                        } else {
                            messages.push('WordPress エラー: ' + (data.wordpress.error || '不明なエラー'));
                        }
                    }
                    const wpSuccess = data.wordpress && data.wordpress.success;
                    showStatus(messages.join('\n'), wpSuccess ? 'success' : 'error');

                    if (data.gbp_text) {
                        gbpText = data.gbp_text;
                        gbpSearchUrl = data.gbp_search_url || '';
                        gbpTextEl.textContent = gbpText;
                        gbpSection.classList.remove('hidden');
                    }
                }
            } catch (e) {
                showStatus('通信エラーが発生しました: ' + e.message, 'error');
            } finally {
                btnUpload.disabled = false;
                btnUpload.textContent = 'WordPressにアップロード';
            }
        });

        btnGbp.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(gbpText);
                btnGbp.textContent = 'コピーしました！';
                setTimeout(() => {
                    btnGbp.textContent = 'コピーしてGBPを開く';
                }, 2000);
            } catch (e) {
                btnGbp.textContent = 'コピー失敗...';
                setTimeout(() => {
                    btnGbp.textContent = 'コピーしてGBPを開く';
                }, 2000);
            }
            if (gbpSearchUrl) {
                window.open(gbpSearchUrl, '_blank');
            }
        });
    </script>
</body>
</html>
```

- [ ] **Step 2: Add GBP section styles to static/style.css**

Append to end of file:

```css

.gbp-section {
    margin-top: 24px;
    padding: 20px;
    background-color: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 8px;
}

.gbp-section.hidden {
    display: none;
}

.gbp-section h2 {
    font-size: 0.95rem;
    font-weight: 600;
    color: #0c4a6e;
    margin-bottom: 12px;
}

.gbp-text {
    padding: 12px;
    background-color: #ffffff;
    border: 1px solid #e0f2fe;
    border-radius: 6px;
    font-size: 0.9rem;
    color: #1e293b;
    line-height: 1.6;
    margin-bottom: 12px;
    white-space: pre-line;
}

.btn-gbp {
    background-color: #0284c7;
    color: #ffffff;
}

.btn-gbp:hover:not(:disabled) {
    background-color: #0369a1;
}
```

- [ ] **Step 3: Run all tests**

Run: `pytest tests/ -v`

Expected: All tests PASS (index route still renders correctly)

- [ ] **Step 4: Commit**

```bash
git add templates/index.html static/style.css
git commit -m "feat: rewrite UI - manual input, GBP copy button"
```

---

### Task 5: Update deploy config

**Files:**
- Modify: `deploy/setup.sh`
- Modify: `deploy/gold-uploader.service`

- [ ] **Step 1: Update deploy/setup.sh**

Replace entire file with:

```bash
#!/bin/bash
# VPS initial setup script
# Usage: sudo bash setup.sh YOUR_DOMAIN

set -euo pipefail

DOMAIN="${1:?ドメインを指定してください（例: gold.example.com）}"
APP_DIR="/opt/gold-price-uploader"

echo "=== System update ==="
apt update && apt upgrade -y

echo "=== Install packages ==="
apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx ufw

echo "=== Firewall ==="
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "=== Auto-updates ==="
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

echo "=== App directory ==="
mkdir -p "$APP_DIR"
cp -r . "$APP_DIR/"

echo "=== Python venv ==="
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "=== .env check ==="
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "WARNING: Edit .env file: $APP_DIR/.env"
fi

echo "=== Basic auth user ==="
echo "Enter Basic auth password:"
htpasswd -c /etc/nginx/.htpasswd goldadmin

echo "=== Nginx config ==="
cp deploy/nginx.conf /etc/nginx/sites-available/gold-uploader
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" /etc/nginx/sites-available/gold-uploader
ln -sf /etc/nginx/sites-available/gold-uploader /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "=== SSL certificate ==="
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN"

echo "=== Systemd service ==="
cp deploy/gold-uploader.service /etc/systemd/system/
chown -R www-data:www-data "$APP_DIR"
systemctl daemon-reload
systemctl enable gold-uploader
systemctl start gold-uploader

echo "=== Setup complete ==="
echo "Site: https://$DOMAIN"
echo ""
echo "Next steps:"
echo "1. Edit .env: $APP_DIR/.env"
echo "2. Restart: systemctl restart gold-uploader"
echo "3. Disable SSH password: PasswordAuthentication no in /etc/ssh/sshd_config"
```

- [ ] **Step 2: Update deploy/gold-uploader.service**

Replace entire file with:

```ini
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
    --timeout 60 \
    wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Commit**

```bash
git add deploy/setup.sh deploy/gold-uploader.service
git commit -m "chore: remove Playwright from deploy config"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run full test suite**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && source venv/bin/activate && pytest tests/ -v`

Expected: All tests PASS

- [ ] **Step 2: Manual smoke test**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && source venv/bin/activate && python -c "from app import create_app; app = create_app(); print('App created OK')"`

Expected: "App created OK"

- [ ] **Step 3: Run the app locally and verify in browser**

Run: `cd /Users/atsushishibazaki/Desktop/googlenews && source venv/bin/activate && flask --app wsgi:app run --port 5001`

Open: `http://localhost:5001/gold/`

Verify:
- Form is visible immediately (no fetch button)
- Can enter prices and date
- Upload button works
- GBP section appears after upload
- Copy button copies text and opens Google search

- [ ] **Step 4: Commit any fixes if needed, then tag**

```bash
git tag v2.0.0-simplified
```
