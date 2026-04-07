<?php
// ============================================================
// 金価格アップロードツール（PHP単体版）
// 設置: f-high-class.jp サーバーに配置
// ============================================================

// --- 設定 ---
define('AUTH_USER', 'admin');
define('AUTH_PASS', 'goldprice2026');
define('WP_SITE_URL', 'https://f-high-class.jp');
define('WP_USERNAME', 'f-high-class');
define('WP_APP_PASSWORD', 'S1Yc t6Ut adUM WCL3 nB4r qFiO');
define('WP_PAGE_ID', 666);
define('GBP_SEARCH_URL', 'https://www.google.com/search?q=フリマハイクラス');

// --- Basic認証 ---
if (!isset($_SERVER['PHP_AUTH_USER'])
    || $_SERVER['PHP_AUTH_USER'] !== AUTH_USER
    || $_SERVER['PHP_AUTH_PW'] !== AUTH_PASS) {
    header('WWW-Authenticate: Basic realm="Gold Admin"');
    header('HTTP/1.0 401 Unauthorized');
    echo '認証が必要です';
    exit;
}

// --- WordPress REST API更新 ---
$result = null;
$gbp_text = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['retail_price'])) {
    $retail_price  = trim($_POST['retail_price']);
    $purchase_price = trim($_POST['purchase_price']);
    $price_date    = trim($_POST['date']);

    // バリデーション
    if (!preg_match('/^[\d,]+$/', $retail_price)) {
        $result = ['success' => false, 'message' => '小売価格は数値のみ入力してください'];
    } elseif ($purchase_price !== '' && !preg_match('/^[\d,]+$/', $purchase_price)) {
        $result = ['success' => false, 'message' => '買取価格は数値のみ入力してください'];
    } elseif ($price_date === '') {
        $result = ['success' => false, 'message' => '日付を入力してください'];
    } else {
        if ($purchase_price === '') {
            $purchase_price = $retail_price;
        }

        // WordPress固定ページ用HTML
        $content = '<div class="gold-price-container">
  <p class="gold-price-date">' . htmlspecialchars($price_date, ENT_QUOTES, 'UTF-8') . ' 現在</p>
  <table class="gold-price-table">
    <tr>
      <th>金小売価格（税込）</th>
      <td>' . htmlspecialchars($retail_price, ENT_QUOTES, 'UTF-8') . ' 円/g</td>
    </tr>
    <tr>
      <th>金買取価格（税込）</th>
      <td>' . htmlspecialchars($purchase_price, ENT_QUOTES, 'UTF-8') . ' 円/g</td>
    </tr>
  </table>
</div>';

        // cURLでWordPress REST API呼び出し
        $api_url = WP_SITE_URL . '/wp-json/wp/v2/pages/' . WP_PAGE_ID;
        $ch = curl_init($api_url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
            CURLOPT_USERPWD        => WP_USERNAME . ':' . WP_APP_PASSWORD,
            CURLOPT_POSTFIELDS     => json_encode(['content' => $content]),
            CURLOPT_TIMEOUT        => 15,
        ]);
        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curl_error = curl_error($ch);
        curl_close($ch);

        if ($curl_error) {
            $result = ['success' => false, 'message' => '通信エラー: ' . $curl_error];
        } elseif ($http_code >= 200 && $http_code < 300) {
            $data = json_decode($response, true);
            $link = $data['link'] ?? '';
            $result = ['success' => true, 'message' => 'WordPressの固定ページを更新しました', 'link' => $link];
        } else {
            $result = ['success' => false, 'message' => 'WordPress更新エラー (HTTP ' . $http_code . ')'];
        }

        // GBP投稿テキスト生成
        $gbp_text = $price_date . '本日K18/1g  ' . $purchase_price . '円でお買い取りしております。';
    }
}
?>
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>金価格アップロードツール</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif;
            background-color: #f0f2f5;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }

        .container {
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.10);
            padding: 40px 36px;
            width: 100%;
            max-width: 480px;
        }

        h1 {
            font-size: 1.4rem;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 28px;
            text-align: center;
            letter-spacing: 0.02em;
        }

        .btn {
            display: block;
            width: 100%;
            padding: 14px;
            font-size: 1rem;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.2s ease, opacity 0.2s ease;
            font-family: inherit;
        }

        .btn:disabled { opacity: 0.6; cursor: not-allowed; }

        .btn-upload { background-color: #ea580c; color: #ffffff; margin-top: 8px; }
        .btn-upload:hover:not(:disabled) { background-color: #c2410c; }

        .price-form {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .form-group label {
            font-size: 0.875rem;
            font-weight: 600;
            color: #374151;
        }

        .input-row {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .form-group input[type="text"] {
            flex: 1;
            padding: 10px 12px;
            font-size: 1rem;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            text-align: right;
            font-family: inherit;
            color: #111827;
            transition: border-color 0.15s ease;
        }

        .form-group input[type="text"]:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }

        .unit {
            font-size: 0.875rem;
            color: #6b7280;
            white-space: nowrap;
        }

        .status {
            margin-top: 20px;
            padding: 14px 16px;
            border-radius: 8px;
            font-size: 0.9rem;
            line-height: 1.6;
        }

        .status.success {
            background-color: #dcfce7;
            color: #166534;
            border: 1px solid #86efac;
        }

        .status.error {
            background-color: #fee2e2;
            color: #991b1b;
            border: 1px solid #fca5a5;
        }

        .gbp-section {
            margin-top: 24px;
            padding: 20px;
            background-color: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
        }

        .gbp-section h2 {
            font-size: 0.95rem;
            font-weight: 600;
            color: #0c4a6e;
            margin-bottom: 12px;
        }

        .gbp-text {
            padding: 12px;
            background-color: #ffffff;
            border: 1px solid #e0f2fe;
            border-radius: 6px;
            font-size: 0.9rem;
            color: #1e293b;
            line-height: 1.6;
            margin-bottom: 12px;
        }

        .btn-gbp { background-color: #0284c7; color: #ffffff; }
        .btn-gbp:hover:not(:disabled) { background-color: #0369a1; }
    </style>
</head>
<body>
    <div class="container">
        <h1>金価格アップロードツール</h1>

        <?php if ($result): ?>
            <div class="status <?= $result['success'] ? 'success' : 'error' ?>">
                <?= htmlspecialchars($result['message'], ENT_QUOTES, 'UTF-8') ?>
                <?php if (!empty($result['link'])): ?>
                    <br><a href="<?= htmlspecialchars($result['link'], ENT_QUOTES, 'UTF-8') ?>" target="_blank">ページを確認</a>
                <?php endif; ?>
            </div>
        <?php endif; ?>

        <?php if ($gbp_text): ?>
            <div class="gbp-section">
                <h2>GBP投稿用テキスト</h2>
                <div class="gbp-text" id="gbp-text"><?= htmlspecialchars($gbp_text, ENT_QUOTES, 'UTF-8') ?></div>
                <button class="btn btn-gbp" onclick="copyAndOpenGbp()">コピーしてGBPを開く</button>
            </div>
        <?php endif; ?>

        <form method="post" class="price-form">
            <div class="form-group">
                <label for="retail-price">小売価格</label>
                <div class="input-row">
                    <input type="text" id="retail-price" name="retail_price"
                           placeholder="例: 26,200"
                           value="<?= htmlspecialchars($_POST['retail_price'] ?? '', ENT_QUOTES, 'UTF-8') ?>">
                    <span class="unit">円/g</span>
                </div>
            </div>
            <div class="form-group">
                <label for="purchase-price">買取価格</label>
                <div class="input-row">
                    <input type="text" id="purchase-price" name="purchase_price"
                           placeholder="例: 25,000"
                           value="<?= htmlspecialchars($_POST['purchase_price'] ?? '', ENT_QUOTES, 'UTF-8') ?>">
                    <span class="unit">円/g</span>
                </div>
            </div>
            <div class="form-group">
                <label for="price-date">日付</label>
                <input type="text" id="price-date" name="date"
                       placeholder="例: 4月7日"
                       value="<?= htmlspecialchars($_POST['date'] ?? '', ENT_QUOTES, 'UTF-8') ?>">
            </div>
            <button type="submit" class="btn btn-upload">WordPressにアップロード</button>
        </form>
    </div>

    <script>
        function copyAndOpenGbp() {
            const text = document.getElementById('gbp-text').textContent;
            navigator.clipboard.writeText(text).then(() => {
                const btn = document.querySelector('.btn-gbp');
                btn.textContent = 'コピーしました！';
                setTimeout(() => { btn.textContent = 'コピーしてGBPを開く'; }, 2000);
            }).catch(() => {
                const btn = document.querySelector('.btn-gbp');
                btn.textContent = 'コピー失敗...';
                setTimeout(() => { btn.textContent = 'コピーしてGBPを開く'; }, 2000);
            });
            window.open(<?= json_encode(GBP_SEARCH_URL) ?>, '_blank');
        }
    </script>
</body>
</html>
