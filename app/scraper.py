import re
from datetime import date
from typing import Optional

import requests
from bs4 import BeautifulSoup


def _extract_price(value_text: str) -> str:
    """価格テキストから数値（カンマ区切り）を抽出する。

    例:
        '14,589円'        -> '14,589'
        '27,065 円(+420 円)' -> '27,065'
    """
    match = re.search(r"[\d,]+", value_text)
    if not match:
        raise ValueError(f"価格の数値が見つかりません: {value_text!r}")
    return match.group(0)


def scrape_gold_price(url: Optional[str] = None, html: Optional[str] = None) -> dict:
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
            if "小売" in header_text:
                retail_price = _extract_price(value_text)
            elif "買取" in header_text:
                purchase_price = _extract_price(value_text)

    if retail_price is None or purchase_price is None:
        raise ValueError(
            "金価格の取得に失敗しました。ページ構造が変更された可能性があります。"
        )

    return {
        "retail_price": retail_price,
        "purchase_price": purchase_price,
        "date": date.today().isoformat(),
    }
