# 金価格アップロード PHP単体ファイル版

## 背景

Flask版で実装した金価格アップロードツールを、PHPファイル1枚に変換する。
レンタルサーバー（f-high-class.jp）にファイルを置くだけで動作する。

## 構成

- ファイル1枚: `gold-admin.php`
- 設置場所: f-high-class.jp のサーバー（WordPress `/site/` と同階層）
- アクセス制限: PHPファイル内でBasic認証

## 機能

1. Basic認証でアクセス制限
2. フォームに小売価格・買取価格・日付を手入力
3. 「アップロード」→ WordPress REST API で固定ページ（ID:666）を更新
4. GBP投稿テキストを表示＋「コピーしてGBPを開く」ボタン

## 処理フロー

1. ブラウザでアクセス → Basic認証
2. フォーム表示（小売価格、買取価格、日付）
3. 送信 → PHPがcURLでWordPress REST APIを呼び出し
4. 結果表示（成功/エラー）＋ GBPテキスト＋コピーボタン

## WordPress API

- エンドポイント: `https://f-high-class.jp/wp-json/wp/v2/pages/666`
- メソッド: POST
- 認証: HTTPBasicAuth（f-high-class / App Password）
- ボディ: `{"content": "<HTML>"}` — 固定ページのコンテンツを更新
- PHPの `cURL` を使用（WordPress外の単体PHPなので wp_remote_post は使えない）

## HTMLコンテンツ（WordPress固定ページに書き込む内容）

```html
<div class="gold-price-container">
  <p class="gold-price-date">{日付} 現在</p>
  <table class="gold-price-table">
    <tr>
      <th>金小売価格（税込）</th>
      <td>{小売価格} 円/g</td>
    </tr>
    <tr>
      <th>金買取価格（税込）</th>
      <td>{買取価格} 円/g</td>
    </tr>
  </table>
</div>
```

## GBP投稿テキスト

お客様の既存投稿パターンに合わせる:

```
{日付}本日K18/1g  {買取価格}円でお買い取りしております。
```

## Basic認証

- PHPファイル冒頭で `$_SERVER['PHP_AUTH_USER']` / `$_SERVER['PHP_AUTH_PW']` をチェック
- ID/パスワードはPHPファイル内に定数定義
- 認証失敗時は 401 レスポンス

## 設定値（PHP定数）

```php
define('AUTH_USER', 'admin');
define('AUTH_PASS', 'パスワード');
define('WP_SITE_URL', 'https://f-high-class.jp');
define('WP_USERNAME', 'f-high-class');
define('WP_APP_PASSWORD', 'S1Yc t6Ut adUM WCL3 nB4r qFiO');
define('WP_PAGE_ID', 666);
define('GBP_SEARCH_URL', 'https://www.google.com/search?q=フリマハイクラス');
```

## バリデーション

- 小売価格: 必須、数値とカンマのみ
- 買取価格: 任意、空なら小売価格を使用
- 日付: 必須、数値・スラッシュ・日本語のみ

## UI

Flask版と同等のデザイン。HTML/CSS/JSをPHPファイル内にインライン記述。
- フォームは最初から表示
- アップロード後にGBPセクション表示
- 「コピーしてGBPを開く」ボタン: クリップボードコピー＋Google検索を新タブで開く
