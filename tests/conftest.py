import os

# テスト実行時に必要な環境変数をダミー値でセット（.envがない環境でも動作するように）
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
os.environ.setdefault("WP_SITE_URL", "https://example.com")
os.environ.setdefault("WP_USERNAME", "admin")
os.environ.setdefault("WP_APP_PASSWORD", "xxxx-xxxx-xxxx-xxxx")
os.environ.setdefault("WP_PAGE_ID", "123")
os.environ.setdefault("GOOGLE_ACCOUNT_ID", "accounts/123456789")
os.environ.setdefault("GOOGLE_LOCATION_ID", "locations/123456789")
