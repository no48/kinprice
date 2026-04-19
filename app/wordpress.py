from datetime import datetime, timedelta, timezone
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth

JST = timezone(timedelta(hours=9))


def update_gold_page(
    site_url: str,
    username: str,
    app_password: str,
    page_id: int,
    gold_scrap: Optional[dict] = None,
    pt_scrap: Optional[dict] = None,
) -> dict:
    """WordPressの固定ページを貴金属価格で更新する。"""
    content = _build_page_content(
        gold_scrap or {}, pt_scrap or {},
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

COIN_DEFS = [
    ("天皇陛下御即位記念10万円金貨", 30.0),
    ("天皇陛下御在位60年記念10万円金貨", 20.0),
    ("皇太子殿下御成婚記念5万円金貨", 18.0),
    ("天皇陛下御在位記念1万円金貨", 20.0),
    ("長野五輪冬季大会記念1万円金貨", 15.6),
]


def _build_coin_rows(k22_price: str) -> str:
    """K22単価 × 重量で金貨価格を計算する。K22がなければ空文字。"""
    if not k22_price:
        return ""
    try:
        unit = float(str(k22_price).replace(",", ""))
    except ValueError:
        return ""
    lines = []
    for name, weight in COIN_DEFS:
        price = int(round(unit * weight))
        lines.append(
            f"      <tr>\n        <th>{name}</th>\n        <td>{price:,}円</td>\n      </tr>"
        )
    return "\n".join(lines) + "\n"


def _today_jst_ja() -> str:
    """JSTの今日の日付を '2026年04月19日' 形式で返す。"""
    return datetime.now(JST).strftime("%Y年%m月%d日")


def _build_page_content(
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

    coin_rows_html = _build_coin_rows(gold_scrap.get("K22", ""))

    formatted_date = _today_jst_ja()

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
{coin_rows_html}    </tbody>
    </table>
  </div>
</div>
"""
