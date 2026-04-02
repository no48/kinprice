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
) -> dict:
    """WordPressの固定ページを金価格で更新する。

    Args:
        site_url: WordPressサイトのURL（例: https://example.com）
        username: WordPressユーザー名
        app_password: WordPressアプリケーションパスワード
        page_id: 更新対象の固定ページID
        retail_price: 小売価格（カンマ付き文字列）
        purchase_price: 買取価格（カンマ付き文字列）
        price_date: 日付文字列

    Returns:
        dict: success, message, link を含む辞書
    """
    content = _build_page_content(retail_price, purchase_price, price_date)

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


def _build_page_content(
    retail_price: str, purchase_price: str, price_date: str
) -> str:
    """固定ページ用のHTMLコンテンツを生成する。"""
    return f"""
<div class="gold-price-container">
  <p class="gold-price-date">{price_date} 現在</p>
  <table class="gold-price-table">
    <tr>
      <th>金小売価格（税込）</th>
      <td>{retail_price} 円/g</td>
    </tr>
    <tr>
      <th>金買取価格（税込）</th>
      <td>{purchase_price} 円/g</td>
    </tr>
  </table>
</div>
"""
