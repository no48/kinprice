# GBP投稿：コピー＋ブラウザ誘導方式

## 背景

Google Business Profile APIの投稿（localPosts）機能は廃止済み。新APIにも投稿機能はない。
Playwright自動化はGoogleログインの不安定さとメンテナンスコストが高く、お客様への納品に不向き。

## 方針

WordPress投稿は従来通りAPI自動投稿。GBP投稿は「テキストコピー＋Google検索ページを開く」方式に変更し、お客様が手動で貼り付ける。

## お客様の操作フロー

1. 操作画面で「価格を取得」ボタン押下 → 金価格がスクレイピングされる
2. 必要に応じて価格を修正
3. 「アップロード」ボタン押下 → WordPressが自動更新される
4. 画面にGBP投稿テキストが表示される
5. 「コピーしてGBPを開く」ボタン押下 → テキストがクリップボードにコピー＋Google検索「フリマハイクラス」が新タブで開く
6. Google検索結果で「最新情報を追加」をクリック → 貼り付け → 投稿

## 変更箇所

### 1. UI（templates/index.html）

- 「Googleビジネスプロフィールに投稿」チェックボックスを削除
- アップロード成功後のエリアに以下を追加：
  - GBP投稿テキストの表示欄
  - 「コピーしてGBPを開く」ボタン
- ボタンのJS処理：
  - `navigator.clipboard.writeText()` でテキストコピー
  - `window.open(GBP_SEARCH_URL, '_blank')` で新タブ
  - ボタンテキストを「コピーしました！」に一時変更

### 2. ルーティング（app/routes.py）

- `/upload` のPOSTハンドラから Google API呼び出しを削除
- `post_to_google` フラグの処理を削除
- レスポンスJSONに `gbp_text` フィールドを追加（GBP投稿用テキスト）

### 3. google_business.py

- ファイルを削除

### 4. 設定（app/config.py, .env）

- Google関連設定を削除：GOOGLE_ACCOUNT_ID, GOOGLE_LOCATION_ID, GOOGLE_CREDENTIALS_PATH
- GBP検索URL設定を追加：GBP_SEARCH_URL

### 5. テスト

- tests/test_google_business.py を削除
- tests/test_routes.py からGoogle関連テストを削除・更新
- GBPテキスト生成の新テストを追加

### 6. 依存関係（requirements.txt）

- google-auth, google-api-python-client を削除

## GBP投稿テキストの形式

現在のお客様の投稿パターンに合わせる：

```
{日付}本日K18/1g  {買取価格}円でお買い取りしております。
```

## 設定値

- GBP_SEARCH_URL: `https://www.google.com/search?q=フリマハイクラス`
