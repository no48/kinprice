from typing import Optional
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
    gold_scrap: Optional[dict] = None,
    pt_scrap: Optional[dict] = None,
) -> dict:
    """WordPressの固定ページを貴金属価格で更新する。"""
    content = _build_page_content(
        retail_price, purchase_price, price_date,
        gold_scrap or {}, pt_scrap or {},
    )

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


GOLD_SCRAP_ORDER = ["K24", "K18", "K14"]
PT_SCRAP_ORDER = ["Pt1000", "Pt900", "Pt850"]

GOLD_SCRAP_LABELS = {"K24": "K24（インゴット）", "K18": "K18", "K14": "K14"}
PT_SCRAP_LABELS = {"Pt1000": "Pt1000（インゴット）", "Pt900": "Pt900", "Pt850": "Pt850"}


def _build_page_content(
    retail_price: str,
    purchase_price: str,
    price_date: str,
    gold_scrap: dict,
    pt_scrap: dict,
) -> str:
    """固定ページ用のHTMLコンテンツを生成する。"""
    gold_rows = "".join(
        f'    <tr><th>{GOLD_SCRAP_LABELS[k]}</th><td>{gold_scrap[k]} 円/g</td></tr>\n'
        for k in GOLD_SCRAP_ORDER
        if k in gold_scrap and gold_scrap[k]
    )
    pt_rows = "".join(
        f'    <tr><th>{PT_SCRAP_LABELS[k]}</th><td>{pt_scrap[k]} 円/g</td></tr>\n'
        for k in PT_SCRAP_ORDER
        if k in pt_scrap and pt_scrap[k]
    )

    gold_section = f"""  <h3>金買取価格（税込）</h3>
  <table class="gold-price-table">
    <tr><th>金インゴット小売価格</th><td>{retail_price} 円/g</td></tr>
    <tr><th>金インゴット買取価格</th><td>{purchase_price} 円/g</td></tr>
{gold_rows}  </table>
"""

    pt_section = ""
    if pt_rows:
        pt_section = f"""  <h3>プラチナ買取価格（税込）</h3>
  <table class="gold-price-table">
{pt_rows}  </table>
"""

    return f"""
<div class="gold-price-container">
  <p class="gold-price-date">{price_date} 現在</p>
{gold_section}{pt_section}</div>
"""
