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

    # 自社サイト（フリマハイクラス）の現在公開中の買取価格ページ。画面を開いた時の初期値に使う。
    PUBLISHED_SOURCE_URL = os.environ.get(
        "PUBLISHED_SOURCE_URL",
        "https://f-high-class.jp/",
    )

    # GBP
    GBP_SEARCH_URL = os.environ.get(
        "GBP_SEARCH_URL",
        "https://www.google.com/search?q=フリマハイクラス",
    )

    # Basic認証
    BASIC_AUTH_USERNAME = os.environ["BASIC_AUTH_USERNAME"]
    BASIC_AUTH_PASSWORD = os.environ["BASIC_AUTH_PASSWORD"]
