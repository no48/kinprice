# 当店マージン適用＋日付編集機能 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ネットジャパン取得値から自店買取価格を自動計算し画面初期値に反映、日付欄を編集可能にし、「日付のみ更新」機能を追加する。

**Architecture:** マージン定数と計算ロジックを `app/margins.py` に切り出し、`/fetch` レスポンスを `reference`+`adjusted`+`date` に拡張。WP更新は既存 `update_gold_page` を日付引数対応に改修し、別途 `update_date_only_on_wp` 関数で日付部分のみ置換するエンドポイントを追加。フロント `templates/index.html` で日付編集可・新ボタン対応。

**Tech Stack:** Python 3.11 / Flask / requests / pytest / Vanilla JS（フレームワーク無し）

**仕様書:** `docs/superpowers/specs/2026-05-02-gold-price-margin-and-date-edit-design.md`

---

## Task 1: マージン計算モジュール作成（純粋ロジック・TDD）

**Files:**
- Create: `app/margins.py`
- Create: `tests/test_margins.py`

- [ ] **Step 1-1: 失敗するテストを書く**

`tests/test_margins.py` に以下を作成：

```python
"""app/margins.py の単体テスト。"""
import pytest
from app.margins import floor10, compute_adjusted


def test_floor10_truncates_ones_digit():
    assert floor10(25_614) == 25_610
    assert floor10(25_619) == 25_610
    assert floor10(25_610) == 25_610
    assert floor10(0) == 0
    assert floor10(9) == 0


def test_compute_adjusted_k24():
    """K24 = floor10(NJ K24) - 170"""
    raw = _raw_with(retail_price="26,352")
    assert compute_adjusted(raw)["K24"] == "26,180"


def test_compute_adjusted_k22():
    """K22 = floor10(自店K24 - 900)。NJのK22は使わない。"""
    raw = _raw_with(retail_price="26,352", k22="99,999")  # K22は無視される
    result = compute_adjusted(raw)
    # K24自店=26,180 → 26,180-900=25,280 → floor10=25,280
    assert result["K22"] == "25,280"


def test_compute_adjusted_k18_passthrough():
    """K18 はNJ値をそのまま返す（マージン適用なし）。"""
    raw = _raw_with(k18="19,553")
    assert compute_adjusted(raw)["K18"] == "19,553"


def test_compute_adjusted_k14():
    """K14 = floor10(NJ K14) - 400"""
    raw = _raw_with(k14="14,494")
    # 14,490 - 400 = 14,090
    assert compute_adjusted(raw)["K14"] == "14,090"


def test_compute_adjusted_pt1000():
    raw = _raw_with(pt1000="10,849")
    # 10,840 - 200 = 10,640
    assert compute_adjusted(raw)["Pt1000"] == "10,640"


def test_compute_adjusted_pt900():
    raw = _raw_with(pt900="9,921")
    # 9,920 - 50 = 9,870
    assert compute_adjusted(raw)["Pt900"] == "9,870"


def test_compute_adjusted_pt850():
    raw = _raw_with(pt850="9,362")
    # 9,360 - 80 = 9,280
    assert compute_adjusted(raw)["Pt850"] == "9,280"


def test_compute_adjusted_full_example():
    """仕様書の総合例（2026/04/24時点のNJ値）。"""
    raw = {
        "retail_price": "26,352",
        "gold_scrap": {"K24": "25,614", "K22": "23,216", "K18": "19,553", "K14": "14,494"},
        "pt_scrap":   {"Pt1000": "10,849", "Pt950": "10,290", "Pt900": "9,921", "Pt850": "9,362"},
    }
    result = compute_adjusted(raw)
    assert result == {
        "K24":    "26,180",
        "K22":    "25,280",
        "K18":    "19,553",
        "K14":    "14,090",
        "Pt1000": "10,640",
        "Pt900":  "9,870",
        "Pt850":  "9,280",
    }


def _raw_with(retail_price="26,352", k22="23,216", k18="19,553", k14="14,494",
              pt1000="10,849", pt900="9,921", pt850="9,362"):
    return {
        "retail_price": retail_price,
        "gold_scrap": {"K24": "0", "K22": k22, "K18": k18, "K14": k14},
        "pt_scrap":   {"Pt1000": pt1000, "Pt900": pt900, "Pt850": pt850},
    }
```

- [ ] **Step 1-2: テストが失敗することを確認**

```bash
source venv/bin/activate && pytest tests/test_margins.py -v
```
Expected: ImportError（`app.margins` が存在しない）

- [ ] **Step 1-3: `app/margins.py` を実装**

```python
"""自店買取価格のマージン計算。"""

# 各銘柄のマージン（円）。変更時はここを編集。
MARGIN_K24    = 170
MARGIN_K22    = 900   # 自店K24から引く額（NJのK22は使わない）
MARGIN_K14    = 400
MARGIN_PT1000 = 200
MARGIN_PT900  = 50
MARGIN_PT850  = 80


def floor10(yen: int) -> int:
    """一の位を切り捨てて10円単位にする。例: 25,614 → 25,610"""
    return (yen // 10) * 10


def _to_int(price_str: str) -> int:
    return int(str(price_str).replace(",", ""))


def _fmt(yen: int) -> str:
    return f"{yen:,}"


def compute_adjusted(raw: dict) -> dict:
    """ネットジャパン生値から自店買取価格を計算する。

    Args:
        raw: scrape_gold_price() の返り値（retail_price, gold_scrap, pt_scrap を含む）

    Returns:
        K24/K22/K18/K14/Pt1000/Pt900/Pt850 の文字列辞書
    """
    nj_k24    = _to_int(raw["retail_price"])
    nj_k18    = raw["gold_scrap"]["K18"]
    nj_k14    = _to_int(raw["gold_scrap"]["K14"])
    nj_pt1000 = _to_int(raw["pt_scrap"]["Pt1000"])
    nj_pt900  = _to_int(raw["pt_scrap"]["Pt900"])
    nj_pt850  = _to_int(raw["pt_scrap"]["Pt850"])

    k24 = floor10(nj_k24) - MARGIN_K24
    k22 = floor10(k24 - MARGIN_K22)

    return {
        "K24":    _fmt(k24),
        "K22":    _fmt(k22),
        "K18":    nj_k18,
        "K14":    _fmt(floor10(nj_k14) - MARGIN_K14),
        "Pt1000": _fmt(floor10(nj_pt1000) - MARGIN_PT1000),
        "Pt900":  _fmt(floor10(nj_pt900)  - MARGIN_PT900),
        "Pt850":  _fmt(floor10(nj_pt850)  - MARGIN_PT850),
    }
```

- [ ] **Step 1-4: テストが通ることを確認**

```bash
source venv/bin/activate && pytest tests/test_margins.py -v
```
Expected: 8 passed

- [ ] **Step 1-5: コミット**

```bash
git add app/margins.py tests/test_margins.py
git commit -m "$(cat <<'EOF'
feat: 自店買取価格を計算するmarginsモジュールを追加

ネットジャパン参考値から各銘柄のマージン適用後の当店買取価格を
計算する純粋ロジックを独立モジュールとして実装。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `wordpress.py` の日付引数対応＋関数公開

**Files:**
- Modify: `app/wordpress.py`
- Modify: `tests/test_wordpress.py`

これまで `update_gold_page` 内で `_today_jst_ja()` が呼ばれていたため、ユーザーが入力した日付を反映できなかった。日付を引数で受け取る形に変更し、関数を公開（プライベートの `_` を外す）する。

- [ ] **Step 2-1: 失敗するテストを書く**

`tests/test_wordpress.py` の末尾に追加：

```python
from app.wordpress import update_gold_page, today_jst_ja


def test_today_jst_ja_returns_japanese_date_format():
    """today_jst_ja() は 'YYYY年MM月DD日' 形式を返す。"""
    import re
    result = today_jst_ja()
    assert re.match(r"^\d{4}年\d{2}月\d{2}日$", result)


def test_update_gold_page_uses_provided_date():
    """page_date 引数で渡された日付がページ内容に反映される。"""
    with patch("app.wordpress.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "link": "https://example.com/gold"}
        mock_post.return_value = mock_response

        update_gold_page(
            site_url="https://example.com",
            username="admin",
            app_password="test-pass",
            page_id=123,
            gold_scrap={"K24": "25,000", "K18": "19,000", "K14": "14,000"},
            pt_scrap={"Pt1000": "11,000", "Pt900": "10,000", "Pt850": "9,000"},
            page_date="2026年05月02日",
        )

        body = mock_post.call_args_list[1].kwargs["json"]["content"]
        assert "2026年05月02日" in body


def test_update_gold_page_falls_back_to_today_when_no_date():
    """page_date が未指定なら today_jst_ja() を使う（後方互換）。"""
    with patch("app.wordpress.requests.post") as mock_post, \
         patch("app.wordpress.today_jst_ja", return_value="2026年12月31日"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "link": ""}
        mock_post.return_value = mock_response

        update_gold_page(
            site_url="https://example.com",
            username="admin",
            app_password="x",
            page_id=123,
            gold_scrap={"K18": "19,000"},
            pt_scrap={},
        )

        body = mock_post.call_args_list[1].kwargs["json"]["content"]
        assert "2026年12月31日" in body
```

- [ ] **Step 2-2: テストが失敗することを確認**

```bash
source venv/bin/activate && pytest tests/test_wordpress.py -v
```
Expected: ImportError（`today_jst_ja` 公開関数なし）と `update_gold_page` シグネチャエラー

- [ ] **Step 2-3: `app/wordpress.py` を修正**

`_today_jst_ja` を `today_jst_ja` に名前変更し、`update_gold_page` と `_build_page_content` に `page_date` 引数を追加：

```python
def today_jst_ja() -> str:
    """JSTの今日の日付を 'YYYY年MM月DD日' 形式で返す。"""
    return datetime.now(JST).strftime("%Y年%m月%d日")


def update_gold_page(
    site_url: str,
    username: str,
    app_password: str,
    page_id: int,
    gold_scrap: Optional[dict] = None,
    pt_scrap: Optional[dict] = None,
    page_date: Optional[str] = None,
) -> dict:
    """WordPressの固定ページを貴金属価格で更新する。"""
    content = _build_page_content(
        gold_scrap or {}, pt_scrap or {}, page_date,
    )
    # ... 以降は既存と同じ ...
```

`_build_page_content` の修正：

```python
def _build_page_content(
    gold_scrap: dict,
    pt_scrap: dict,
    page_date: Optional[str] = None,
) -> str:
    # ... rows/coin_rows_html を組み立てる既存処理 ...
    formatted_date = page_date if page_date else today_jst_ja()
    return f"""<div class="top_gold_wrap">
    ...
    """
```

既存の `_today_jst_ja` への参照は `today_jst_ja` に置換すること。

- [ ] **Step 2-4: テストが通ることを確認**

```bash
source venv/bin/activate && pytest tests/test_wordpress.py -v
```
Expected: 既存2件＋新規3件 = 5 passed

- [ ] **Step 2-5: コミット**

```bash
git add app/wordpress.py tests/test_wordpress.py
git commit -m "$(cat <<'EOF'
feat: update_gold_pageが任意の日付を受け取れるよう対応

ユーザー入力の日付をWordPressページに反映できるようにするため、
page_date引数を追加。未指定時は今日のJSTを使う後方互換動作を維持。
today_jst_jaを公開関数に変更。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `update_date_only_on_wp` 関数追加

**Files:**
- Modify: `app/wordpress.py`
- Modify: `tests/test_wordpress.py`

WordPress固定ページのHTMLから日付文字列だけを置換するための関数。

- [ ] **Step 3-1: 失敗するテストを書く**

`tests/test_wordpress.py` の末尾に追加：

```python
from app.wordpress import update_date_only_on_wp


def test_update_date_only_replaces_date_in_existing_content():
    """既存ページのHTMLから日付だけを置換する。"""
    existing_html = '<p class="date">2026年04月20日    現在の買取金額</p>'
    with patch("app.wordpress.requests.get") as mock_get, \
         patch("app.wordpress.requests.post") as mock_post:
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {"content": {"raw": existing_html}}
        mock_get.return_value = mock_get_resp
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"link": "https://example.com/gold"}
        mock_post.return_value = mock_post_resp

        result = update_date_only_on_wp(
            site_url="https://example.com",
            username="admin",
            app_password="x",
            page_id=123,
            new_date="2026年05月02日",
        )

        assert result["success"] is True
        sent_body = mock_post.call_args.kwargs["json"]["content"]
        assert "2026年05月02日" in sent_body
        assert "2026年04月20日" not in sent_body


def test_update_date_only_returns_error_when_no_date_pattern():
    """既存ページに日付パターンが無い場合はエラーを返す（POSTしない）。"""
    with patch("app.wordpress.requests.get") as mock_get, \
         patch("app.wordpress.requests.post") as mock_post:
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {"content": {"raw": "<p>no date here</p>"}}
        mock_get.return_value = mock_get_resp

        result = update_date_only_on_wp(
            site_url="https://example.com",
            username="admin",
            app_password="x",
            page_id=123,
            new_date="2026年05月02日",
        )

        assert result["success"] is False
        assert "見つかりません" in result["error"]
        mock_post.assert_not_called()


def test_update_date_only_handles_api_error():
    """WP API GET失敗時にエラー情報を返す。"""
    with patch("app.wordpress.requests.get") as mock_get:
        mock_get_resp = MagicMock()
        mock_get_resp.raise_for_status.side_effect = Exception("Unauthorized")
        mock_get.return_value = mock_get_resp

        result = update_date_only_on_wp(
            site_url="https://example.com",
            username="admin",
            app_password="x",
            page_id=123,
            new_date="2026年05月02日",
        )
        assert result["success"] is False
        assert "error" in result
```

- [ ] **Step 3-2: テストが失敗することを確認**

```bash
source venv/bin/activate && pytest tests/test_wordpress.py -v -k update_date_only
```
Expected: ImportError

- [ ] **Step 3-3: `app/wordpress.py` に関数追加**

ファイル末尾に追加：

```python
import re
# （既存のimportに re を追加してもよい）


def update_date_only_on_wp(
    site_url: str,
    username: str,
    app_password: str,
    page_id: int,
    new_date: str,
) -> dict:
    """WordPress固定ページのHTML内の日付文字列のみを置換する。

    `\\d{4}年\\d{2}月\\d{2}日` の最初のマッチを new_date に置換する。
    マッチがなければエラーを返す。
    """
    api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}"
    auth = HTTPBasicAuth(username, app_password)
    try:
        get_response = requests.get(api_url, auth=auth, timeout=15)
        get_response.raise_for_status()
        current = get_response.json().get("content", {}).get("raw", "")

        new_content, count = re.subn(
            r"\d{4}年\d{2}月\d{2}日", new_date, current, count=1
        )
        if count == 0:
            return {
                "success": False,
                "error": "ページ内に日付パターンが見つかりません",
            }

        post_response = requests.post(
            api_url,
            json={"content": new_content},
            auth=auth,
            timeout=15,
        )
        post_response.raise_for_status()
        return {
            "success": True,
            "message": "日付を更新しました",
            "link": post_response.json().get("link", ""),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"WordPress更新エラー: {str(e)}",
        }
```

- [ ] **Step 3-4: テストが通ることを確認**

```bash
source venv/bin/activate && pytest tests/test_wordpress.py -v
```
Expected: 全件 passed

- [ ] **Step 3-5: コミット**

```bash
git add app/wordpress.py tests/test_wordpress.py
git commit -m "$(cat <<'EOF'
feat: WP固定ページの日付のみを置換する関数を追加

価格表は変えず日付文字列だけを差し替えるため、GETしてHTMLから
'YYYY年MM月DD日' パターンを正規表現置換しPOSTで書き戻す関数を実装。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `/fetch` レスポンスを `reference`+`adjusted`+`date` に拡張

**Files:**
- Modify: `app/routes.py`
- Modify: `tests/test_routes.py`

既存の `retail_price`/`gold_scrap`/`pt_scrap` をそのまま返す形をやめ、画面が直接使う形に整形する。

- [ ] **Step 4-1: 失敗するテストを書く**

`tests/test_routes.py` の `/fetch` セクションに追加：

```python
def test_fetch_returns_date_reference_and_adjusted(client, app):
    prefix = get_prefix(app)
    mock_raw = {
        "retail_price": "26,352",
        "date": "2026/04/24 09:30",
        "gold_scrap": {"K24": "25,614", "K22": "23,216", "K18": "19,553", "K14": "14,494"},
        "pt_scrap":   {"Pt1000": "10,849", "Pt950": "10,290", "Pt900": "9,921", "Pt850": "9,362"},
        "silver_scrap": {"Sv1000": "392", "Sv925": "352"},
    }
    with patch("app.routes.scrape_gold_price", return_value=mock_raw):
        res = client.post(f"{prefix}/fetch")
    assert res.status_code == 200
    data = res.get_json()
    # 当日のJST日付（YYYY年MM月DD日）
    import re
    assert re.match(r"^\d{4}年\d{2}月\d{2}日$", data["date"])
    # NJ生値が reference に
    assert data["reference"]["K24"] == "26,352"
    assert data["reference"]["K18"] == "19,553"
    assert data["reference"]["Pt900"] == "9,921"
    # 当店計算値が adjusted に
    assert data["adjusted"]["K24"] == "26,180"
    assert data["adjusted"]["K22"] == "25,280"
    assert data["adjusted"]["K18"] == "19,553"   # K18はそのまま
    assert data["adjusted"]["K14"] == "14,090"
    assert data["adjusted"]["Pt1000"] == "10,640"
    assert data["adjusted"]["Pt900"] == "9,870"
    assert data["adjusted"]["Pt850"] == "9,280"
    assert "source_url" in data
```

既存の `test_fetch_returns_json` は新しい構造に合わせて書き換える：

```python
def test_fetch_returns_json(client, app):
    prefix = get_prefix(app)
    mock_raw = {
        "retail_price": "26,200",
        "date": "2026/04/06 09:30",
        "gold_scrap": {"K24": "25,000", "K22": "22,000", "K18": "19,000", "K14": "14,000"},
        "pt_scrap":   {"Pt1000": "11,000", "Pt900": "10,000", "Pt850": "9,000"},
    }
    with patch("app.routes.scrape_gold_price", return_value=mock_raw):
        res = client.post(f"{prefix}/fetch")
    assert res.status_code == 200
    data = res.get_json()
    assert "reference" in data
    assert "adjusted" in data
    assert "date" in data
```

- [ ] **Step 4-2: テストが失敗することを確認**

```bash
source venv/bin/activate && pytest tests/test_routes.py -v -k fetch
```
Expected: 新規テストが KeyError 等で失敗

- [ ] **Step 4-3: `app/routes.py` を修正**

冒頭のimportに追加：

```python
from app.margins import compute_adjusted
from app.wordpress import update_gold_page, today_jst_ja, update_date_only_on_wp
```

`/fetch` ハンドラを書き換え：

```python
@bp.route("/fetch", methods=["POST"])
def fetch_price():
    try:
        url = current_app.config["GOLD_SOURCE_URL"]
        raw = scrape_gold_price(url=url)
        adjusted = compute_adjusted(raw)
        return jsonify({
            "date": today_jst_ja(),
            "reference": {
                "K24":    raw["retail_price"],
                "K22":    raw["gold_scrap"].get("K22", ""),
                "K18":    raw["gold_scrap"].get("K18", ""),
                "K14":    raw["gold_scrap"].get("K14", ""),
                "Pt1000": raw["pt_scrap"].get("Pt1000", ""),
                "Pt900":  raw["pt_scrap"].get("Pt900", ""),
                "Pt850":  raw["pt_scrap"].get("Pt850", ""),
            },
            "adjusted": adjusted,
            "source_url": url,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

- [ ] **Step 4-4: テストが通ることを確認**

```bash
source venv/bin/activate && pytest tests/test_routes.py -v -k fetch
```
Expected: passed

- [ ] **Step 4-5: コミット**

```bash
git add app/routes.py tests/test_routes.py
git commit -m "$(cat <<'EOF'
feat: /fetchで参考値と当店計算値を分けて返す

画面が「参考: NJ値」「初期値: 自店計算値」を別々に扱えるよう、
レスポンスを {date, reference, adjusted, source_url} に再編。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `/upload` で日付を WP へ反映

**Files:**
- Modify: `app/routes.py`
- Modify: `tests/test_routes.py`

これまで `/upload` は日付を受け取っても WordPress 本文には反映していなかった（GBPテキストにだけ使用）。Task 2 で `update_gold_page` が `page_date` を受け取れるようになったため、これを渡す。

- [ ] **Step 5-1: 失敗するテストを書く**

`tests/test_routes.py` の `/upload` セクションに追加：

```python
def test_upload_passes_date_to_wordpress(client, app):
    prefix = get_prefix(app)
    payload = _valid_payload(date="2026年05月02日")
    wp_result = {"success": True, "message": "OK"}
    with patch("app.routes.update_gold_page", return_value=wp_result) as mock_wp:
        client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
        # update_gold_page が page_date="2026年05月02日" で呼ばれること
        assert mock_wp.call_args.kwargs["page_date"] == "2026年05月02日"
```

`_valid_payload` の `date` の既定値も新形式に揃える：

```python
def _valid_payload(**overrides):
    payload = {
        "date": "2026年05月02日",   # YYYY年MM月DD日 形式に統一
        "gold_scrap": {"K24": "25,000", "K18": "19,000", "K14": "14,000"},
        "pt_scrap": {"Pt1000": "11,000", "Pt900": "10,000", "Pt850": "9,000"},
    }
    payload.update(overrides)
    return payload
```

`test_upload_returns_gbp_text` の `date` 期待値を修正（`"4月4日"` のままでも動作するが、新形式に統一）：

```python
def test_upload_returns_gbp_text(client, app):
    prefix = get_prefix(app)
    payload = _valid_payload(date="2026年05月02日")
    wp_result = {"success": True, "message": "OK"}
    with patch("app.routes.update_gold_page", return_value=wp_result):
        res = client.post(
            f"{prefix}/upload",
            data=json.dumps(payload),
            content_type="application/json",
        )
    data = res.get_json()
    assert "gbp_text" in data
    assert "19,000" in data["gbp_text"]
    assert "2026年05月02日" in data["gbp_text"]
```

- [ ] **Step 5-2: テストが失敗することを確認**

```bash
source venv/bin/activate && pytest tests/test_routes.py -v -k upload
```
Expected: `test_upload_passes_date_to_wordpress` で AssertionError

- [ ] **Step 5-3: `app/routes.py` の `/upload` を修正**

`update_gold_page` 呼び出しに `page_date=price_date` を追加：

```python
if post_to_wp:
    wp_result = update_gold_page(
        site_url=current_app.config["WP_SITE_URL"],
        username=current_app.config["WP_USERNAME"],
        app_password=current_app.config["WP_APP_PASSWORD"],
        page_id=current_app.config["WP_PAGE_ID"],
        gold_scrap=gold_scrap,
        pt_scrap=pt_scrap,
        page_date=price_date,
    )
    results["wordpress"] = wp_result
```

加えて `date_pattern` バリデーションは緩いままで OK（既存パターンが日本語日付も許容している）。

- [ ] **Step 5-4: テストが通ることを確認**

```bash
source venv/bin/activate && pytest tests/test_routes.py -v
```
Expected: 全件 passed

- [ ] **Step 5-5: コミット**

```bash
git add app/routes.py tests/test_routes.py
git commit -m "$(cat <<'EOF'
feat: /uploadのdateをWPページにも反映

これまでGBPテキストにしか使われていなかった日付を、
WordPress固定ページ本文にも反映するようupdate_gold_pageへ
page_date引数で渡す。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `/update-date` エンドポイント追加

**Files:**
- Modify: `app/routes.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 6-1: 失敗するテストを書く**

`tests/test_routes.py` の末尾に追加：

```python
# ---------------------------------------------------------------------------
# /update-date
# ---------------------------------------------------------------------------

def test_update_date_success(client, app):
    prefix = get_prefix(app)
    wp_result = {"success": True, "message": "日付を更新しました", "link": "https://example.com/gold"}
    with patch("app.routes.update_date_only_on_wp", return_value=wp_result) as mock_wp:
        res = client.post(
            f"{prefix}/update-date",
            data=json.dumps({"date": "2026年05月02日"}),
            content_type="application/json",
        )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert mock_wp.call_args.kwargs["new_date"] == "2026年05月02日"


def test_update_date_rejects_invalid_format(client, app):
    prefix = get_prefix(app)
    res = client.post(
        f"{prefix}/update-date",
        data=json.dumps({"date": "2026/05/02"}),  # スラッシュ形式は不可
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "形式" in res.get_json()["error"]


def test_update_date_rejects_empty(client, app):
    prefix = get_prefix(app)
    res = client.post(
        f"{prefix}/update-date",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert res.status_code == 400


def test_update_date_returns_500_on_wp_error(client, app):
    prefix = get_prefix(app)
    wp_result = {"success": False, "error": "WordPress更新エラー: timeout"}
    with patch("app.routes.update_date_only_on_wp", return_value=wp_result):
        res = client.post(
            f"{prefix}/update-date",
            data=json.dumps({"date": "2026年05月02日"}),
            content_type="application/json",
        )
    assert res.status_code == 500
    assert "error" in res.get_json()
```

- [ ] **Step 6-2: テストが失敗することを確認**

```bash
source venv/bin/activate && pytest tests/test_routes.py -v -k update_date
```
Expected: 404（エンドポイント無し）

- [ ] **Step 6-3: `app/routes.py` にハンドラを追加**

`/upload` ハンドラの直後に追加：

```python
@bp.route("/update-date", methods=["POST"])
def update_date():
    try:
        data = request.get_json(silent=True) or {}
        new_date = (data.get("date") or "").strip()
        if not re.match(r"^\d{4}年\d{2}月\d{2}日$", new_date):
            return jsonify({"error": "日付の形式が不正です（YYYY年MM月DD日）"}), 400

        result = update_date_only_on_wp(
            site_url=current_app.config["WP_SITE_URL"],
            username=current_app.config["WP_USERNAME"],
            app_password=current_app.config["WP_APP_PASSWORD"],
            page_id=current_app.config["WP_PAGE_ID"],
            new_date=new_date,
        )
        if not result.get("success"):
            return jsonify({"error": result.get("error", "")}), 500
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"サーバーエラー: {type(e).__name__}: {str(e)}"}), 500
```

- [ ] **Step 6-4: テストが通ることを確認**

```bash
source venv/bin/activate && pytest tests/test_routes.py -v
```
Expected: 全件 passed

- [ ] **Step 6-5: コミット**

```bash
git add app/routes.py tests/test_routes.py
git commit -m "$(cat <<'EOF'
feat: /update-dateエンドポイントを追加

価格を変えずWPページ本文の日付だけを書き換える専用エンドポイント。
入力フォーマット（YYYY年MM月DD日）のバリデーションとWP API失敗時の
エラーハンドリングを含む。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: フロント `templates/index.html` 改修

**Files:**
- Modify: `templates/index.html`

UIテストはサーバ側テストでカバーされているため、ここはコード差分＋手動確認のみ。

- [ ] **Step 7-1: 日付欄を編集可能にする**

`<input type="text" id="price-date" name="date" readonly>` から `readonly` を削除：

```html
<input type="text" id="price-date" name="date">
```

- [ ] **Step 7-2: 「日付のみ更新」ボタンを追加**

既存の `<button id="btn-upload">WordPressにアップロード</button>` の直後に追加：

```html
<button type="button" id="btn-update-date" class="btn btn-update-date">日付のみ更新</button>
```

- [ ] **Step 7-3: JS の `btnFetch` ハンドラを新レスポンス形式に対応**

`btnFetch.addEventListener('click', ...)` 内の以下のブロックを書き換える：

変更前：
```javascript
priceDateEl.value = data.date || '';
priceForm.classList.remove('hidden');

if (data.source_url) {
    sourceLinkEl.href = data.source_url;
    sourceLinkEl.textContent = data.source_url;
    sourceLinkWrap.classList.remove('hidden');
}

const goldScrap = Object.assign({}, data.gold_scrap || {});
if (data.retail_price) {
    goldScrap.K24 = data.retail_price;
}

renderScrapGrid(
    document.getElementById('gold-scrap-grid'),
    document.getElementById('gold-scrap-section'),
    goldScrap,
    GOLD_SCRAP_KEYS
);
renderScrapGrid(
    document.getElementById('pt-scrap-grid'),
    document.getElementById('pt-scrap-section'),
    data.pt_scrap || {},
    PT_SCRAP_KEYS
);
```

変更後：
```javascript
priceDateEl.value = data.date || '';
priceForm.classList.remove('hidden');

if (data.source_url) {
    sourceLinkEl.href = data.source_url;
    sourceLinkEl.textContent = data.source_url;
    sourceLinkWrap.classList.remove('hidden');
}

const reference = data.reference || {};
const adjusted = data.adjusted || {};

renderScrapGridWithRef(
    document.getElementById('gold-scrap-grid'),
    document.getElementById('gold-scrap-section'),
    adjusted, reference, GOLD_SCRAP_KEYS
);
renderScrapGridWithRef(
    document.getElementById('pt-scrap-grid'),
    document.getElementById('pt-scrap-section'),
    adjusted, reference, PT_SCRAP_KEYS
);
```

- [ ] **Step 7-4: 新しい `renderScrapGridWithRef` 関数を追加**

既存の `renderScrapGrid` を置き換える形で以下を追加：

```javascript
function renderScrapGridWithRef(gridEl, sectionEl, adjusted, reference, allowedKeys) {
    gridEl.innerHTML = '';
    const visibleKeys = allowedKeys.filter(k => adjusted[k] !== undefined);
    if (visibleKeys.length === 0) {
        sectionEl.classList.add('hidden');
        return;
    }
    sectionEl.classList.remove('hidden');
    visibleKeys.forEach(key => {
        const refValue = reference[key] || '';
        const initValue = adjusted[key] || '';
        const row = document.createElement('div');
        row.className = 'scrap-row';
        row.innerHTML =
            '<span class="scrap-label">' + SCRAP_LABELS[key] + '</span>' +
            '<span class="scrap-ref">参考: ' + refValue + '円</span>' +
            '<span class="scrap-input-wrap">' +
                '<input type="text" class="scrap-input" data-key="' + key + '" value="' + initValue + '" data-ref="' + refValue + '">' +
                '<span class="unit">円</span>' +
            '</span>';
        gridEl.appendChild(row);
    });
}
```

旧 `renderScrapGrid` は削除する。

- [ ] **Step 7-5: 「日付のみ更新」ボタンのハンドラを追加**

`btnGbp.addEventListener` の直前あたりに追加：

```javascript
const btnUpdateDate = document.getElementById('btn-update-date');

btnUpdateDate.addEventListener('click', async () => {
    const newDate = priceDateEl.value.trim();
    if (!/^\d{4}年\d{2}月\d{2}日$/.test(newDate)) {
        alert('日付の形式が不正です（例: 2026年05月02日）');
        return;
    }

    btnUpdateDate.disabled = true;
    btnUpdateDate.textContent = '更新中...';
    hideStatus();

    try {
        const res = await fetch(BASE_URL + '/update-date', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: newDate }),
        });
        const data = await res.json();
        if (data.error) {
            showStatus('エラー: ' + data.error, 'error');
        } else {
            showStatus('日付を更新しました: ' + newDate, 'success');
        }
    } catch (e) {
        showStatus('通信エラーが発生しました: ' + e.message, 'error');
    } finally {
        btnUpdateDate.disabled = false;
        btnUpdateDate.textContent = '日付のみ更新';
    }
});
```

- [ ] **Step 7-6: 動作確認（手動）**

ローカルでFlaskを起動し、ブラウザで動作を確認：

```bash
source venv/bin/activate && \
  FLASK_SECRET_KEY=dev FLASK_APP=wsgi.py \
  WP_SITE_URL=https://example.invalid \
  WP_USERNAME=x WP_APP_PASSWORD=x WP_PAGE_ID=1 \
  GBP_SEARCH_URL=https://example.invalid \
  BASIC_AUTH_USERNAME=admin BASIC_AUTH_PASSWORD=password \
  APP_URL_PREFIX=/gold \
  flask run --port 5000
```

ブラウザで `http://localhost:5000/gold/`（admin/password）を開き：
- [価格を取得] → 日付欄に今日のJST日付、各価格欄に当店計算値、参考はNJ生値
- 日付欄が手で編集できる
- [日付のみ更新] ボタンが表示される（実APIに繋がる場合は WP_SITE_URL を本物に）

- [ ] **Step 7-7: コミット**

```bash
git add templates/index.html
git commit -m "$(cat <<'EOF'
feat: 日付編集可・当店計算値の初期表示・日付のみ更新ボタン

- 日付欄の readonly を解除し編集可能化
- /fetch の adjusted/reference に対応した renderScrapGridWithRef を追加
- 「日付のみ更新」ボタンと /update-date 呼び出し処理を追加

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: 全テスト＆スモークテストで完了確認

**Files:** （変更なし）

- [ ] **Step 8-1: 全テスト実行**

```bash
source venv/bin/activate && pytest -v
```
Expected: 全件 passed（増分含めて 35件前後）

- [ ] **Step 8-2: 実サイトを使った/fetch動作確認**

```bash
source venv/bin/activate && python -c "
import os
os.environ.update({
    'FLASK_SECRET_KEY':'dev', 'WP_SITE_URL':'https://example.invalid',
    'WP_USERNAME':'x', 'WP_APP_PASSWORD':'x', 'WP_PAGE_ID':'1',
    'GBP_SEARCH_URL':'https://example.invalid',
    'BASIC_AUTH_USERNAME':'admin', 'BASIC_AUTH_PASSWORD':'password',
    'APP_URL_PREFIX':'/gold',
})
from app import create_app
app = create_app()
client = app.test_client()
import base64
auth = base64.b64encode(b'admin:password').decode()
r = client.post('/gold/fetch', headers={'Authorization': f'Basic {auth}'})
print('status:', r.status_code)
import json
data = json.loads(r.data)
print('date:', data.get('date'))
print('reference K24:', data['reference']['K24'])
print('adjusted K24:', data['adjusted']['K24'])
print('adjusted K22:', data['adjusted']['K22'])
print('adjusted K18:', data['adjusted']['K18'])
"
```
Expected: status 200、当日のJST日付、reference と adjusted の両方が表示される

- [ ] **Step 8-3: ブラウザで全フローを確認**

ローカルFlask起動 → ブラウザで操作：
1. [価格を取得] でフォームが出ることを確認
2. 日付欄を「2026年05月03日」など別の値に書き換え可能
3. [WordPressにアップロード] のpayloadに新日付が含まれることを DevTools で確認（実WPなしでも /upload はエラーで返る、payloadだけ確認）
4. [日付のみ更新] のpayloadが `{ "date": "2026年05月03日" }` になっていることを DevTools で確認

- [ ] **Step 8-4: 仕上げのコミット（必要なら）**

微調整があれば追加コミット。なければスキップ。

- [ ] **Step 8-5: 最終確認**

```bash
git log --oneline -10
```
今回の機能追加の各コミットが綺麗に並んでいることを確認。

---

## 完了基準

- [ ] `pytest` が全件パス
- [ ] `/fetch` が `{date, reference, adjusted, source_url}` を返す
- [ ] `/upload` が指定された日付をWordPressへ反映
- [ ] `/update-date` が日付のみ置換し、不正な形式は400で拒否
- [ ] フロントの日付欄が編集可能、初期値=今日のJST、新ボタン動作
- [ ] 既存テスト（auth, scraper, GBP, バリデーション）が壊れていない
