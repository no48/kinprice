from datetime import date
from typing import Optional

from playwright.sync_api import sync_playwright


def scrape_gold_price(url: Optional[str] = None, html: Optional[str] = None) -> dict:
    """ネットジャパンのサイトから金の買取価格を取得する。

    Args:
        url: スクレイピング先URL
        html: テスト用にHTMLを直接渡す場合（Playwrightを使わずパースのみ）

    Returns:
        dict: retail_price (買取価格), date を含む辞書
    """
    if html is not None:
        return _parse_from_html(html)

    if url is None:
        raise ValueError("url or html must be provided")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")

        # Wait for price data to load
        page.wait_for_selector("p.text", timeout=15000)

        # Get the date/time
        date_text = ""
        all_p = page.query_selector_all("p.text")
        for el in all_p:
            text = el.inner_text().strip()
            if "/" in text and ":" in text:  # matches "2026/04/02 11:30"
                date_text = text
                break

        # Get gold price - find the element containing "金" and get the next sibling price
        price_value = None
        for i, el in enumerate(all_p):
            text = el.inner_text().strip()
            if text == "金":
                # Next element should be the price
                if i + 1 < len(all_p):
                    price_value = all_p[i + 1].inner_text().strip()
                break

        browser.close()

    if price_value is None:
        raise ValueError("金価格の取得に失敗しました。ページ構造が変更された可能性があります。")

    return {
        "retail_price": price_value,
        "date": date_text,
    }


def _parse_from_html(html: str) -> dict:
    """テスト用: 固定HTMLからパースする（Playwrightを使わない）"""
    import re
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    price_value = None
    date_text = date.today().isoformat()

    all_p = soup.find_all("p", class_="text")
    for i, el in enumerate(all_p):
        text = el.get_text(strip=True)
        if re.match(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", text):
            date_text = text
        if text == "金" and i + 1 < len(all_p):
            price_value = all_p[i + 1].get_text(strip=True)
            break

    if price_value is None:
        raise ValueError("金価格の取得に失敗しました。")

    return {
        "retail_price": price_value,
        "date": date_text,
    }
