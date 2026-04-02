from app.scraper import scrape_gold_price

SAMPLE_HTML = """
<html>
<body>
<table>
<tr><th>店頭小売価格(税込)</th><td>14,589円</td></tr>
<tr><th>店頭買取価格(税込)</th><td>14,200円</td></tr>
</table>
</body>
</html>
"""

# 実際の田中貴金属サイトに近いHTML（前日比を含む形式）
REAL_SITE_HTML = """
<html>
<body>
<table>
<tr><th>店頭小売価格（税込）（小売価格前日比）</th><td>27,065 円(+420 円)</td></tr>
<tr><th>店頭買取価格（税込）（買取価格前日比）</th><td>26,708 円(+420 円)</td></tr>
</table>
</body>
</html>
"""


def test_scrape_gold_price_parses_prices():
    """固定HTMLから小売・買取価格を正しく抽出できる"""
    result = scrape_gold_price(html=SAMPLE_HTML)
    assert result["retail_price"] == "14,589"
    assert result["purchase_price"] == "14,200"


def test_scrape_gold_price_parses_real_site_format():
    """実サイト形式（前日比付き）から価格を正しく抽出できる"""
    result = scrape_gold_price(html=REAL_SITE_HTML)
    assert result["retail_price"] == "27,065"
    assert result["purchase_price"] == "26,708"


def test_scrape_gold_price_includes_date():
    """結果に日付が含まれる"""
    result = scrape_gold_price(html=SAMPLE_HTML)
    assert "date" in result
