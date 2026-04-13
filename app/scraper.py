from datetime import date
from typing import Optional

from playwright.sync_api import sync_playwright


# スクラップ価格のラベル定義
GOLD_SCRAP_LABELS = ["K24", "K22", "K21.6", "K20", "K18", "K14", "K10", "K9"]
PT_SCRAP_LABELS = ["Pt1000", "Pt950", "Pt900", "Pt850"]
SILVER_SCRAP_LABELS = ["Sv1000", "Sv925"]


def scrape_gold_price(url: Optional[str] = None, html: Optional[str] = None) -> dict:
    """ネットジャパンのサイトから貴金属の買取価格を取得する。

    Args:
        url: スクレイピング先URL
        html: テスト用にHTMLを直接渡す場合（Playwrightを使わずパースのみ）

    Returns:
        dict: retail_price, date, gold_scrap, pt_scrap, silver_scrap を含む辞書
    """
    if html is not None:
        return _parse_from_html(html)

    if url is None:
        raise ValueError("url or html must be provided")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")

        page.wait_for_selector("p.text", state="attached", timeout=15000)

        all_p = page.query_selector_all("p.text")
        texts = [(el.text_content() or "").strip() for el in all_p]

        browser.close()

    return _parse_texts(texts)


def _parse_texts(texts: list[str]) -> dict:
    """p.text要素のテキストリストから全価格を抽出する。"""
    result = {
        "retail_price": None,
        "date": "",
        "gold_scrap": {},
        "pt_scrap": {},
        "silver_scrap": {},
    }

    i = 0
    while i < len(texts):
        text = texts[i]

        # 日付（例: "2026/04/10 09:30"）
        if "/" in text and ":" in text and len(text) <= 20:
            import re
            if re.match(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", text):
                result["date"] = text

        # 金インゴット価格
        if text == "金" and i + 1 < len(texts):
            result["retail_price"] = texts[i + 1]

        # 金スクラップ
        if text == "金スクラップ":
            scrap = _extract_scrap_prices(texts, i, GOLD_SCRAP_LABELS)
            result["gold_scrap"] = scrap

        # Ptスクラップ
        if text == "Ptスクラップ":
            scrap = _extract_scrap_prices(texts, i, PT_SCRAP_LABELS)
            result["pt_scrap"] = scrap

        # 銀スクラップ
        if text == "銀スクラップ":
            scrap = _extract_scrap_prices(texts, i, SILVER_SCRAP_LABELS)
            result["silver_scrap"] = scrap

        i += 1

    if result["retail_price"] is None:
        raise ValueError("金価格の取得に失敗しました。ページ構造が変更された可能性があります。")

    return result


def _extract_scrap_prices(texts: list[str], start_idx: int, labels: list[str]) -> dict:
    """スクラップセクションからラベルと価格のペアを抽出する。

    ページ構造: [セクション名] [ラベル1] [ラベル2] ... [買取価格（税込）] [価格1] [円] [価格2] [円] ...
    """
    # 「買取価格（税込）」の位置を探す
    price_start = None
    for j in range(start_idx + 1, min(start_idx + len(labels) + 5, len(texts))):
        if texts[j] == "買取価格（税込）":
            price_start = j + 1
            break

    if price_start is None:
        return {}

    # 価格を取得（「円」を飛ばしながら）
    prices = []
    j = price_start
    while j < len(texts) and len(prices) < len(labels):
        if texts[j] != "円":
            prices.append(texts[j])
        j += 1

    return dict(zip(labels, prices))


def _parse_from_html(html: str) -> dict:
    """テスト用: 固定HTMLからパースする（Playwrightを使わない）"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    all_p = soup.find_all("p", class_="text")
    texts = [el.get_text(strip=True) for el in all_p]

    if not texts:
        raise ValueError("金価格の取得に失敗しました。")

    try:
        return _parse_texts(texts)
    except ValueError:
        raise
