import pytest

from app.scraper import scrape_gold_price

# ネットジャパンサイトの実際の構造に合わせたサンプルHTML
SAMPLE_HTML = """
<html>
<body>
<p class="text">2026/04/02 11:30</p>
<p class="text">金</p>
<p class="text">26,200</p>
<p class="text">円/g</p>
<p class="text">前日比</p>
<p class="text">-36</p>
<p class="text">円</p>
</body>
</html>
"""

# 金ブロックのみのシンプルな構造
SIMPLE_HTML = """
<html>
<body>
<p class="text">金</p>
<p class="text">25,000</p>
<p class="text">円/g</p>
</body>
</html>
"""

# 金ブロックがない（エラーケース）
NO_GOLD_HTML = """
<html>
<body>
<p class="text">Pt</p>
<p class="text">5,000</p>
<p class="text">円/g</p>
</body>
</html>
"""


def test_scrape_gold_price_parses_price():
    """固定HTMLから金の買取価格を正しく抽出できる"""
    result = scrape_gold_price(html=SAMPLE_HTML)
    assert result["retail_price"] == "26,200"


def test_scrape_gold_price_includes_date():
    """結果に日付が含まれ、HTMLに記載の日付と一致する"""
    result = scrape_gold_price(html=SAMPLE_HTML)
    assert "date" in result
    assert result["date"] == "2026/04/02 11:30"


def test_scrape_gold_price_simple_html():
    """シンプルな金ブロックからも価格を抽出できる"""
    result = scrape_gold_price(html=SIMPLE_HTML)
    assert result["retail_price"] == "25,000"


def test_scrape_gold_price_raises_when_no_gold():
    """金ブロックがない場合は ValueError を raise する"""
    with pytest.raises(ValueError, match="金価格の取得に失敗しました"):
        scrape_gold_price(html=NO_GOLD_HTML)


def test_scrape_gold_price_raises_without_args():
    """引数なしで呼ぶと ValueError を raise する"""
    with pytest.raises(ValueError, match="url or html must be provided"):
        scrape_gold_price()


@pytest.mark.slow
def test_scrape_gold_price_real_site():
    """実サイトから金価格を取得できる（要ネット接続）"""
    result = scrape_gold_price(url="https://www.net-japan.co.jp/precious_metal_partner/")
    assert "retail_price" in result
    assert "date" in result
    # 価格はカンマ区切りの数値形式であることを確認
    import re
    assert re.match(r"[\d,]+", result["retail_price"]), f"価格の形式が不正: {result['retail_price']}"
    print(f"\n取得結果: {result}")
