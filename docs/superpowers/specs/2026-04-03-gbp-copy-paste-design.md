# 金価格アップロードツール：簡素化リデザイン

## 背景

- Google Business Profile APIの投稿（localPosts）機能は廃止済み
- Playwright（スクレイピング）は不要 — お客様が金価格を手入力する
- 依存関係を減らし、シンプルなFlaskアプリにする

## 方針

- 金価格はお客様が手入力（スクレイピング機能を削除）
- WordPress固定ページはAPI自動投稿
- GBP投稿は「テキストコピー＋Google検索ページを開く」方式

## お客様の操作フロー

1. 操作画面を開く
2. 金価格（小売/買取）と日付を入力
3. 「アップロード」ボタン押下 → WordPressが自動更新される
4. 画面にGBP投稿テキストが表示される
5. 「コピーしてGBPを開く」ボタン押下 → テキストがクリップボードにコピー＋Google検索ページが新タブで開く
6. Google検索結果で「最新情報を追加」→ 貼り付け → 投稿

## 変更箇所

### 1. UI（templates/index.html）

- 「価格を取得」ボタンを削除（手入力に変更）
- フォームを最初から表示（非表示→表示の切り替え不要）
- 「Googleビジネスプロフィールに投稿」チェックボックスを削除
- アップロード成功後に以下を表示：
  - GBP投稿テキスト表示欄
  - 「コピーしてGBPを開く」ボタン
- ボタンのJS処理：
  - `navigator.clipboard.writeText()` でテキストコピー
  - `window.open(GBP_SEARCH_URL, '_blank')` で新タブ
  - ボタンテキストを「コピーしました！」に一時変更

### 2. ルーティング（app/routes.py）

- `/fetch` エンドポイントを削除
- `/upload` からGoogle API呼び出し・`post_to_google` フラグを削除
- レスポンスJSONに `gbp_text` フィールドを追加

### 3. 削除するファイル

- app/scraper.py（スクレイピング不要）
- app/google_business.py（API投稿不要）
- tests/test_scraper.py
- tests/test_google_business.py

### 4. 設定（app/config.py, .env）

- 削除：GOOGLE_ACCOUNT_ID, GOOGLE_LOCATION_ID, GOOGLE_CREDENTIALS_PATH, GOLD_SOURCE_URL
- 追加：GBP_SEARCH_URL
- Playwright関連の設定も不要

### 5. テスト

- tests/test_routes.py からスクレイピング・Google関連テストを削除・更新
- GBPテキスト生成の新テストを追加

### 6. 依存関係（requirements.txt）

- 削除：playwright, google-auth, google-api-python-client, beautifulsoup4
- 残す：flask, gunicorn, requests, python-dotenv, pytest

### 7. デプロイ設定（deploy/）

- Playwright関連の設定を削除（setup.sh, systemd service）
- PaaS対応も容易になる

## GBP投稿テキストの形式

お客様の既存投稿パターンに合わせる：

```
{日付}本日K18/1g  {買取価格}円でお買い取りしております。
```

## 設定値

- GBP_SEARCH_URL: `https://www.google.com/search?q=フリマハイクラス`
