# 当店買取価格マージン適用＋日付編集機能 設計書

- 作成日: 2026-05-02
- 対象アプリ: kinprice（金価格アップロードツール）
- 本番URL: https://kinprice.onrender.com/gold/

## 1. 背景・目的

ネットジャパンから取得した価格は「相場参考値」であり、当店の買取価格は競合状況に応じてマージンを差し引いた値を使用している。現状はオペレーターが取得値を見ながら手で計算し、テキストボックスに入力していたが、**毎回の計算作業を省き、計算済み値を初期表示する**。値はあくまで初期値で、テキストボックスは編集可能のまま残す。

加えて、相場が動かない日でもページ日付だけ更新したい運用があるため、「**日付のみ更新**」機能を追加する。日付欄も手で編集できるようにする。

## 2. 機能要件

### 2.1 マージン自動計算

| 銘柄 | NJ参照元 | 計算式 |
|---|---|---|
| K24 | `retail_price`（インゴット） | `floor10(NJ) - 170` |
| K22 | （NJ値は使わず自店K24基準） | `floor10(自店K24 - 900)` |
| K18 | `gold_scrap.K18` | NJ値そのまま |
| K14 | `gold_scrap.K14` | `floor10(NJ) - 400` |
| Pt1000 | `pt_scrap.Pt1000`（インゴット表記） | `floor10(NJ) - 200` |
| Pt900 | `pt_scrap.Pt900` | `floor10(NJ) - 50` |
| Pt850 | `pt_scrap.Pt850` | `floor10(NJ) - 80` |

`floor10(yen) = (yen // 10) * 10` （一の位を切り捨て）

マージン値はソースコード内のハードコード定数とする（変更時はClaudeに依頼してコード修正＋デプロイ）。

### 2.2 日付編集

- 日付欄は `<input type="text">` の編集可能フィールド
- 初期値は **今日のJST日付**（`YYYY年MM月DD日` 形式、例: `2026年05月02日`）
- アップロード時はテキストボックスの値をそのままWPページに反映

### 2.3 日付のみ更新

- 新規ボタン「日付のみ更新」を追加
- 押下時、WordPress固定ページの**価格部分は触らず、日付文字列のみ書き換える**
- 入力された日付の形式が不正なら400エラー
- WP API失敗時は500＋エラーメッセージ

## 3. アーキテクチャ

### 3.1 ファイル構成（変更点）

```
app/
├── margins.py        ← 新規：マージン定数 + 計算関数
├── routes.py         ← 修正：/fetch のレスポンス拡張、/update-date 追加
├── wordpress.py      ← 修正：update_date_only() 追加、JST日付生成を共通化
├── scraper.py        ← 変更なし
templates/
└── index.html        ← 修正：日付編集可、初期値=計算済み、新ボタン
tests/
└── test_margins.py   ← 新規：マージン計算の単体テスト
└── test_routes.py    ← 修正：/fetch の adjusted/reference 検証、/update-date 追加
```

### 3.2 `app/margins.py`（新規）

```python
MARGIN_K24    = 170
MARGIN_K22    = 900   # 自店K24から引く額
MARGIN_K14    = 400
MARGIN_PT1000 = 200
MARGIN_PT900  = 50
MARGIN_PT850  = 80


def floor10(yen: int) -> int:
    return (yen // 10) * 10


def _to_int(price_str: str) -> int:
    """'25,614' のようなカンマ区切り文字列を int に変換。"""
    return int(str(price_str).replace(",", ""))


def _fmt(yen: int) -> str:
    """int を 'XX,XXX' 形式に整形。"""
    return f"{yen:,}"


def compute_adjusted(raw: dict) -> dict:
    """
    NJ生値 dict（retail_price, gold_scrap, pt_scrap）から自店買取価格を計算。
    返り値は K24/K22/K18/K14/Pt1000/Pt900/Pt850 の文字列辞書。
    """
    nj_k24    = _to_int(raw["retail_price"])
    nj_k18    = raw["gold_scrap"]["K18"]   # そのまま流用（既にカンマ区切り文字列）
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

### 3.3 `app/routes.py`（変更）

```python
@bp.route("/fetch", methods=["POST"])
def fetch_price():
    url = current_app.config["GOLD_SOURCE_URL"]
    raw = scrape_gold_price(url=url)
    adjusted = compute_adjusted(raw)
    return jsonify({
        "date": today_jst_ja(),               # 今日のJST日付（初期値）
        "reference": {                         # 参考表示用にNJ生値だけ抜粋
            "K24":    raw["retail_price"],
            "K22":    raw["gold_scrap"]["K22"],
            "K18":    raw["gold_scrap"]["K18"],
            "K14":    raw["gold_scrap"]["K14"],
            "Pt1000": raw["pt_scrap"]["Pt1000"],
            "Pt900":  raw["pt_scrap"]["Pt900"],
            "Pt850":  raw["pt_scrap"]["Pt850"],
        },
        "adjusted": adjusted,
        "source_url": url,
    })


@bp.route("/update-date", methods=["POST"])
def update_date_only():
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
```

`/upload` は既存通り。日付フィールドはユーザー入力をそのまま使う（現状の `_today_jst_ja()` ハードコードを止めて引数で受け取るよう修正）。

### 3.4 `app/wordpress.py`（変更）

```python
def today_jst_ja() -> str:
    return datetime.now(JST).strftime("%Y年%m月%d日")


def update_gold_page(..., page_date: str | None = None) -> dict:
    """page_date が None なら今日のJSTを使う（後方互換）。"""
    ...


def update_date_only_on_wp(site_url, username, app_password, page_id, new_date) -> dict:
    """WP固定ページの日付文字列だけを置換する。"""
    api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}"
    auth = HTTPBasicAuth(username, app_password)
    try:
        r = requests.get(api_url, auth=auth, timeout=15)
        r.raise_for_status()
        current = r.json().get("content", {}).get("raw", "")
        replaced, count = re.subn(r"\d{4}年\d{2}月\d{2}日", new_date, current, count=1)
        if count == 0:
            return {"success": False, "error": "ページ内に日付パターンが見つかりません"}
        r2 = requests.post(api_url, json={"content": replaced}, auth=auth, timeout=15)
        r2.raise_for_status()
        return {"success": True, "message": "日付を更新しました", "link": r2.json().get("link", "")}
    except Exception as e:
        return {"success": False, "error": f"WordPress更新エラー: {e}"}
```

### 3.5 `templates/index.html`（変更）

- `<input id="price-date" readonly>` → `readonly` を外す
- `/fetch` のレスポンスから `data.adjusted` を input の value に、`data.reference` を「参考: XXX円」表示に使う
- `<button id="btn-update-date">日付のみ更新</button>` を追加
- ボタンのクリックで `POST /update-date {"date": ...}` を投げ、成功時はステータス表示

## 4. データフロー

### 4.1 価格取得＋アップロード

```
[Click: 価格を取得] → POST /fetch
   ↓
{date, reference, adjusted, source_url} を受信
   ↓
日付欄に date、各価格欄に adjusted、参考に reference を表示
   ↓
ユーザーが必要に応じて編集
   ↓
[Click: WordPressにアップロード] → POST /upload
   {date: "2026年05月02日", gold_scrap: {...}, pt_scrap: {...}, post_to_wp: true}
   ↓
WP固定ページのHTMLを再生成して書き戻し
```

### 4.2 日付のみ更新

```
[Click: 日付のみ更新] → POST /update-date
   {date: "2026年05月02日"}
   ↓
WP固定ページのHTMLをGET → 日付正規表現を置換 → POST
   ↓
ステータス表示
```

## 5. テスト

### 5.1 `tests/test_margins.py`（新規）

- `floor10(25_614) == 25_610` / `floor10(25_610) == 25_610` / `floor10(25_619) == 25_610`
- `compute_adjusted({...})` がドキュメント記載の例と一致：
  - NJ K24=26,352 → 自店 K24="26,180", K22="25,280"
  - NJ K14=14,494 → 自店 K14="14,090"
  - NJ Pt1000=10,849 → 自店 Pt1000="10,640"
  - K18 はそのまま素通し
- 入力にカンマがあってもなくても動作する

### 5.2 `tests/test_routes.py`（追記）

- `/fetch` のレスポンスに `date`/`reference`/`adjusted` が含まれる（モックでscraperを差し替え）
- `/update-date` 正常系：モックWP API、200を返す
- `/update-date` 異常系：日付形式不正で400、WP API失敗で500
- 日付パターンが見つからない既存ページに対して400 or 500（成功してはいけない）

## 6. エラー処理

| ケース | 動作 |
|---|---|
| `/fetch` で scraper 失敗 | 既存通り500 + エラーメッセージ |
| `/upload` の日付形式不正 | 400「日付の形式が不正です」 |
| `/update-date` の日付形式不正 | 400「日付の形式が不正です（YYYY年MM月DD日）」 |
| `/update-date` で WPページに日付パターンなし | 500「ページ内に日付パターンが見つかりません」 |
| WP REST API失敗 | 500「WordPress更新エラー: …」 |

## 7. マージン値の変更手順

ハードコード方式のため、変更時は以下の流れになる：

1. ユーザーがClaude Codeに「K14のマージンを-450にして」等を依頼
2. Claudeが `app/margins.py` の定数を修正
3. テストを通す
4. `git push` → Renderが自動再デプロイ（約2〜3分）

## 8. 非要件（やらないこと）

- マージン値のUI編集（要望が出たら追加検討）
- マージン履歴の記録
- 日付の自動形式変換（`YYYY年MM月DD日` 以外は受け付けない）
- 別の貴金属（Pd等）への対応

## 9. 実装範囲外（既存挙動の維持）

- Basic認証
- スクレイピングAPI呼び出し
- 金貨計算（K22単価 × 重量）
- GBP投稿用テキスト
- 「参考値より低い場合の警告」UI
