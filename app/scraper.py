from typing import Optional

import requests


# スクラップ価格のラベル定義
GOLD_SCRAP_LABELS = ["K24", "K22", "K21.6", "K20", "K18", "K14", "K10", "K9"]
PT_SCRAP_LABELS = ["Pt1000", "Pt950", "Pt900", "Pt850"]
SILVER_SCRAP_LABELS = ["Sv1000", "Sv925"]

# ネットジャパンの内部API（Nuxtフロントが利用する公開エンドポイント）
_API_URL = "https://studio-api-proxy-rajzgb4wwq-an.a.run.app/"
_API_ID = "1fd69ca0358b48af9ce7"
_API_REFERER = "https://www.net-japan.co.jp/"

_GOLD_API_KEYS = {
    "K24": "k24", "K22": "k22", "K21.6": "k21_6", "K20": "k20",
    "K18": "k18", "K14": "k14", "K10": "k10", "K9": "k9",
}
_PT_API_KEYS = {"Pt1000": "pt1000", "Pt950": "pt950", "Pt900": "pt900", "Pt850": "pt850"}
_SILVER_API_KEYS = {"Sv1000": "sv1000", "Sv925": "sv925"}


def scrape_gold_price(url: Optional[str] = None, html: Optional[str] = None) -> dict:
    """ネットジャパンの貴金属買取価格を取得する。

    通常は内部JSON APIを直接叩いて取得する（数百ms）。
    htmlを渡した場合はパースのみ行う（テスト用）。

    Returns:
        dict: retail_price, pt_retail_price, date, gold_scrap, pt_scrap, silver_scrap
    """
    if html is not None:
        return _parse_from_html(html)

    if url is None:
        raise ValueError("url or html must be provided")

    return _fetch_from_api()


def _fetch_from_api() -> dict:
    """内部JSON APIから価格データを取得し、整形済みdictで返す。"""
    response = requests.post(
        _API_URL,
        params={"api_id": _API_ID},
        json={"api_id": _API_ID, "params": {}},
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Referer": _API_REFERER,
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    contents = payload.get("contents") or []
    if not contents:
        raise ValueError("APIレスポンスにcontentsが含まれていません。")
    data = contents[0]

    highlight = data.get("highlight") or {}
    retail_price = (highlight.get("gold") or {}).get("price")
    if not retail_price:
        raise ValueError("金価格の取得に失敗しました。APIレスポンス構造が変更された可能性があります。")
    pt_retail_price = (highlight.get("pt") or {}).get("price")
    if not pt_retail_price:
        raise ValueError("プラチナ価格の取得に失敗しました。APIレスポンス構造が変更された可能性があります。")

    scrap = data.get("scrapItems") or {}
    return {
        "retail_price": retail_price,
        "pt_retail_price": pt_retail_price,
        "date": data.get("marketDate", ""),
        "gold_scrap": _map_scrap(scrap.get("gold") or {}, _GOLD_API_KEYS),
        "pt_scrap": _map_scrap(scrap.get("pt") or {}, _PT_API_KEYS),
        "silver_scrap": _map_scrap(scrap.get("silver") or {}, _SILVER_API_KEYS),
    }


# 自社サイト（フリマハイクラス）の現在公開中の買取価格テーブルから取るキー
_PUBLISHED_KEYS = {"K24", "K18", "K14", "Pt1000", "Pt900", "Pt850"}


def scrape_published_price(url: Optional[str] = None, html: Optional[str] = None) -> dict:
    """自社サイト（フリマハイクラス）の現在公開中の買取価格を取得する。

    トップページの <div class="top_gold_wrap"> 内の金額表をパースする。
    htmlを渡した場合はパースのみ行う（テスト用）。

    Returns:
        dict: {"date": "YYYY年MM月DD日", "prices": {"K24": "24,190", ...}}
    """
    if html is None:
        if url is None:
            raise ValueError("url or html must be provided")
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        html = resp.text
    return _parse_published_html(html)


def _parse_published_html(html: str) -> dict:
    """自社サイトのトップHTMLから現在公開中の買取価格を抽出する。"""
    import re

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    wrap = soup.find("div", class_="top_gold_wrap")
    if wrap is None:
        raise ValueError("買取価格テーブルが見つかりません。ページ構造が変更された可能性があります。")

    prices = {}
    for tr in wrap.find_all("tr"):
        th = tr.find("th")
        td = tr.find("td")
        if not th or not td:
            continue
        # "K24（インゴット）" → "K24" のように括弧前のラベルで判定する
        base_label = re.split(r"[（(]", th.get_text(strip=True))[0].strip()
        if base_label not in _PUBLISHED_KEYS:
            continue
        m = re.search(r"[\d,]+", td.get_text(strip=True))  # "24,190円／1g" → "24,190"
        if m:
            prices[base_label] = m.group(0)

    if "K24" not in prices:
        raise ValueError("金価格の取得に失敗しました。ページ構造が変更された可能性があります。")

    date = ""
    date_el = wrap.find("p", class_="date")
    if date_el:
        dm = re.search(r"\d{4}年\d{2}月\d{2}日", date_el.get_text())
        if dm:
            date = dm.group(0)

    return {"date": date, "prices": prices}


def _map_scrap(section: dict, key_map: dict[str, str]) -> dict:
    """APIのscrapItemsセクションを {ラベル: 価格} に変換する。"""
    return {
        label: section[api_key]
        for label, api_key in key_map.items()
        if section.get(api_key)
    }


def _parse_texts(texts: list[str]) -> dict:
    """p.text要素のテキストリストから全価格を抽出する（旧HTMLパース用、テスト互換）。"""
    result = {
        "retail_price": None,
        "pt_retail_price": None,
        "date": "",
        "gold_scrap": {},
        "pt_scrap": {},
        "silver_scrap": {},
    }

    i = 0
    while i < len(texts):
        text = texts[i]

        if "/" in text and ":" in text and len(text) <= 20:
            import re
            if re.match(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", text):
                result["date"] = text

        if text == "金" and i + 1 < len(texts):
            result["retail_price"] = texts[i + 1]

        if text == "金スクラップ":
            result["gold_scrap"] = _extract_scrap_prices(texts, i, GOLD_SCRAP_LABELS)

        if text == "Ptスクラップ":
            result["pt_scrap"] = _extract_scrap_prices(texts, i, PT_SCRAP_LABELS)

        if text == "銀スクラップ":
            result["silver_scrap"] = _extract_scrap_prices(texts, i, SILVER_SCRAP_LABELS)

        i += 1

    if result["retail_price"] is None:
        raise ValueError("金価格の取得に失敗しました。ページ構造が変更された可能性があります。")

    return result


def _extract_scrap_prices(texts: list[str], start_idx: int, labels: list[str]) -> dict:
    """スクラップセクションからラベルと価格のペアを抽出する。

    ページ構造: [セクション名] [ラベル1] [ラベル2] ... [買取価格（税込）] [価格1] [円] [価格2] [円] ...
    """
    price_start = None
    for j in range(start_idx + 1, min(start_idx + len(labels) + 5, len(texts))):
        if texts[j] == "買取価格（税込）":
            price_start = j + 1
            break

    if price_start is None:
        return {}

    prices = []
    j = price_start
    while j < len(texts) and len(prices) < len(labels):
        if texts[j] != "円":
            prices.append(texts[j])
        j += 1

    return dict(zip(labels, prices))


def _parse_from_html(html: str) -> dict:
    """テスト用: 固定HTMLからパースする。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    all_p = soup.find_all("p", class_="text")
    texts = [el.get_text(strip=True) for el in all_p]

    if not texts:
        raise ValueError("金価格の取得に失敗しました。")

    return _parse_texts(texts)
