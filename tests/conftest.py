import os

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
os.environ.setdefault("WP_SITE_URL", "https://example.com")
os.environ.setdefault("WP_USERNAME", "admin")
os.environ.setdefault("WP_APP_PASSWORD", "xxxx-xxxx-xxxx-xxxx")
os.environ.setdefault("WP_PAGE_ID", "123")
os.environ.setdefault("GBP_SEARCH_URL", "https://www.google.com/search?q=test")
os.environ.setdefault("BASIC_AUTH_USERNAME", "testuser")
os.environ.setdefault("BASIC_AUTH_PASSWORD", "testpass")
