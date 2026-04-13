import re
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth


def update_gold_page(
    site_url: str,
    username: str,
    app_password: str,
    page_id: int,
    price_date: str,
    gold_scrap: Optional[dict] = None,
    pt_scrap: Optional[dict] = None,
) -> dict:
    """WordPressの固定ページを貴金属価格で更新する。"""
    content = _build_page_content(
        price_date, gold_scrap or {}, pt_scrap or {},
    )

    api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}"
    auth = HTTPBasicAuth(username, app_password)

    try:
        clear_response = requests.post(
            api_url,
            json={"content": ""},
            auth=auth,
            timeout=15,
        )
        clear_response.raise_for_status()

        response = requests.post(
            api_url,
            json={"content": content},
            auth=auth,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "message": "WordPressの固定ページを更新しました（クリア後に再書き込み）",
            "link": data.get("link", ""),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"WordPress更新エラー: {str(e)}",
        }


PRICE_ROWS = [
    ("K24", "K24（インゴット）", "gold"),
    ("K18", "K18", "gold"),
    ("K14", "K14", "gold"),
    ("Pt1000", "Pt1000（インゴット）", "pt"),
    ("Pt900", "Pt900", "pt"),
    ("Pt850", "Pt850", "pt"),
]

HIGHLIGHT_KEYS = {"K18"}

COIN_ROWS_HTML = """      <tr>
        <th>天皇陛下御即位記念10万円金貨</th>
        <td>680,400円</td>
      </tr>
      <tr>
        <th>天皇陛下御在位60年記念10万円金貨</th>
        <td>453,600円</td>
      </tr>
      <tr>
        <th>皇太子殿下御成婚記念5万円金貨</th>
        <td>408,240円</td>
      </tr>
      <tr>
        <th>天皇陛下御在位記念1万円金貨</th>
        <td>453,600円</td>
      </tr>
      <tr>
        <th>長野五輪冬季大会記念1万円金貨</th>
        <td>353,808円</td>
      </tr>
"""


def _format_date_ja(price_date: str) -> str:
    """'2026/04/12 09:30' や '2026-04-12' を '2026年04月12日' に変換。"""
    m = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", price_date or "")
    if not m:
        return price_date
    y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
    return f"{y}年{mo}月{d}日"


def _build_page_content(
    price_date: str,
    gold_scrap: dict,
    pt_scrap: dict,
) -> str:
    """固定ページ用のHTMLコンテンツを生成する。"""
    rows = []
    for key, label, group in PRICE_ROWS:
        data = gold_scrap if group == "gold" else pt_scrap
        value = data.get(key, "").strip()
        if not value:
            continue
        td = f"<span>{value}円／1g</span>" if key in HIGHLIGHT_KEYS else f"{value}円／1g"
        rows.append(f"  <tr>\n    <th>{label}</th>\n    <td>{td}</td>\n  </tr>")
    price_rows_html = "\n".join(rows)

    formatted_date = _format_date_ja(price_date)

    return f"""<div class="top_gold_wrap">
  <div class="hl">
    <h4> 地金買取価格<span>Gold</span></h4>
  </div>
  <a href="https://www.f-high-class.jp/kin/"><img src="https://www.f-high-class.jp/site/wp-content/themes/f-high-class/images/top/top_kin.jpg" class="top_kin_img"></a>
  <p class="date">
    {formatted_date}    現在の買取金額</p>
  <div class="inner">
    <table>
      <tbody>
{price_rows_html}
      </tbody>
    </table>
    <table>
      <tbody>
{COIN_ROWS_HTML}    </tbody>
    </table>
  </div>
</div>
"""
