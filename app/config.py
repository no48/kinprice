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
