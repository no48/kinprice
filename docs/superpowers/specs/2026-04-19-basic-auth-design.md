# Basic 認証の導入

## 目的

Render にデプロイしている gold-price-uploader（Flask アプリ）全ルートに Basic 認証をかけ、第三者からのアクセスを防ぐ。

## 要件

- `/gold/`, `/gold/fetch`, `/gold/upload` を含む **全ルート** を認証対象とする
- 認証情報（ユーザー名・パスワード）は **Render の環境変数** で管理する（コードに埋め込まない）
- ライブラリは `Flask-HTTPAuth` を使用（標準的で実装が簡潔）

## アーキテクチャ

### 変更対象ファイル

| ファイル | 変更内容 |
|---|---|
| `requirements.txt` | `Flask-HTTPAuth` を追加 |
| `app/config.py` | `BASIC_AUTH_USERNAME` / `BASIC_AUTH_PASSWORD` を環境変数から読み込む |
| `app/__init__.py` | `HTTPBasicAuth` を初期化し、Blueprint 全体に認証を適用 |
| `render.yaml` | 環境変数 2 つを `sync: false` で追加 |

### 実装詳細

#### `app/config.py`

```python
BASIC_AUTH_USERNAME = os.environ["BASIC_AUTH_USERNAME"]
BASIC_AUTH_PASSWORD = os.environ["BASIC_AUTH_PASSWORD"]
```

環境変数未設定時は起動時に `KeyError` で失敗 → 設定漏れに即気づける。

#### `app/__init__.py`

```python
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()

def create_app():
    app = Flask(...)
    app.config.from_object(Config)

    @auth.verify_password
    def verify_password(username, password):
        if (username == app.config["BASIC_AUTH_USERNAME"]
                and password == app.config["BASIC_AUTH_PASSWORD"]):
            return username
        return None

    from app.routes import bp

    @bp.before_request
    @auth.login_required
    def require_auth():
        pass

    app.register_blueprint(bp, url_prefix=app.config["URL_PREFIX"])
    return app
```

Blueprint の `before_request` フックに `@auth.login_required` を付けることで、blueprint 内の全ルートに認証が適用される。

#### `render.yaml`

```yaml
- key: BASIC_AUTH_USERNAME
  sync: false
- key: BASIC_AUTH_PASSWORD
  sync: false
```

`sync: false` により、値は Render ダッシュボードで手動設定。

## 認証フロー

1. クライアントが `https://kinprice.onrender.com/gold/*` にアクセス
2. サーバーが `401 Unauthorized` + `WWW-Authenticate: Basic` を返す
3. ブラウザが認証ダイアログを表示
4. 正しい認証情報 → 通過 / 誤り → 401 を再度返す

## デプロイ手順（実装後）

1. Render ダッシュボード → サービス `kinprice` → Environment
2. 以下の環境変数を追加：
   - `BASIC_AUTH_USERNAME`: `kayaki-obi_-1`
   - `BASIC_AUTH_PASSWORD`: `d,5c@NW2=eb(`
3. 変更をコミット & push → Render が自動デプロイ
4. `https://kinprice.onrender.com/gold/` にアクセスして認証ダイアログが表示されることを確認

## テスト

- ローカル: `.env` に `BASIC_AUTH_USERNAME` / `BASIC_AUTH_PASSWORD` を追加してアプリ起動 → 認証ダイアログが出ることを確認
- 本番: デプロイ後、正しい認証情報で通過すること・誤った情報で拒否されることを確認

## YAGNI で省いたもの

- ユーザー複数管理
- パスワードのハッシュ化（環境変数に平文保存でOK、攻撃面は Render ダッシュボードのみ）
- レート制限・ログイン試行回数制限
- IP 制限
