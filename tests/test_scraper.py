import pytest

from app.scraper import scrape_gold_price, scrape_published_price

# 自社サイト（フリマハイクラス）トップの実際の構造に合わせたサンプルHTML
PUBLISHED_HTML = """
<div class="top_gold_wrap">
<div class="hl"><h4> 地金買取価格<span>Gold</span></h4><p></p></div>
<p><a href="https://www.f-high-class.jp/kin/"><img src="x.jpg"></a></p>
<p class="date">
    2026年06月07日    現在の買取金額</p>
<div class="inner">
<table><tbody>
<tr><th>K24（インゴット）</th><td>24,190円／1g</td></tr>
<tr><th>K18</th><td><span>18,010円／1g</span></td></tr>
<tr><th>K14</th><td>13,030円／1g</td></tr>
<tr><th>Pt1000（インゴット）</th><td>9,710円／1g</td></tr>
<tr><th>Pt900</th><td>8,730円／1g</td></tr>
<tr><th>Pt850</th><td>8,200円／1g</td></tr>
</tbody></table>
<table><tbody>
<tr><th>天皇陛下御即位記念10万円金貨</th><td>677,700円</td></tr>
<tr><th>長野五輪冬季大会記念1万円金貨</th><td>352,404円</td></tr>
</tbody></table>
</div>
</div>
"""

# ネットジャパンサイトの実際の構造に合わせたサンプルHTML
SAMPLE_HTML = """
<html>
<body>
<p class="text">2026/04/10 09:30</p>
<p class="text">時点</p>
<p class="text">（税込）</p>
<p class="text">金</p>
<p class="text">26,575</p>
<p class="text">円/g</p>
<p class="text">前日比</p>
<p class="text">+338</p>
<p class="text">円</p>
<p class="text">Pt</p>
<p class="text">11,493</p>
<p class="text">円/g</p>
<p class="text">金スクラップ</p>
<p class="text">K24</p>
<p class="text">K22</p>
<p class="text">K21.6</p>
<p class="text">K20</p>
<p class="text">K18</p>
<p class="text">K14</p>
<p class="text">K10</p>
<p class="text">K9</p>
<p class="text">買取価格（税込）</p>
<p class="text">25,831</p>
<p class="text">円</p>
<p class="text">23,413</p>
<p class="text">円</p>
<p class="text">22,987</p>
<p class="text">円</p>
<p class="text">21,393</p>
<p class="text">円</p>
<p class="text">19,719</p>
<p class="text">円</p>
<p class="text">14,616</p>
<p class="text">円</p>
<p class="text">10,152</p>
<p class="text">円</p>
<p class="text">9,036</p>
<p class="text">円</p>
<p class="text">Ptスクラップ</p>
<p class="text">Pt1000</p>
<p class="text">Pt950</p>
<p class="text">Pt900</p>
<p class="text">Pt850</p>
<p class="text">買取価格（税込）</p>
<p class="text">11,148</p>
<p class="text">円</p>
<p class="text">10,574</p>
<p class="text">円</p>
<p class="text">10,194</p>
<p class="text">円</p>
<p class="text">9,620</p>
<p class="text">円</p>
<p class="text">銀スクラップ</p>
<p class="text">Sv1000</p>
<p class="text">Sv925</p>
<p class="text">買取価格（税込）</p>
<p class="text">387</p>
<p class="text">円</p>
<p class="text">348</p>
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
    assert result["retail_price"] == "26,575"


def test_scrape_gold_price_includes_date():
    """結果に日付が含まれ、HTMLに記載の日付と一致する"""
    result = scrape_gold_price(html=SAMPLE_HTML)
    assert result["date"] == "2026/04/10 09:30"


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


def test_scrape_gold_scrap_prices():
    """金スクラップ価格（K24〜K9）を正しく抽出できる"""
    result = scrape_gold_price(html=SAMPLE_HTML)
    gold = result["gold_scrap"]
    assert gold["K24"] == "25,831"
    assert gold["K18"] == "19,719"
    assert gold["K14"] == "14,616"
    assert gold["K10"] == "10,152"
    assert gold["K9"] == "9,036"
    assert len(gold) == 8


def test_scrape_pt_scrap_prices():
    """Ptスクラップ価格（Pt1000〜Pt850）を正しく抽出できる"""
    result = scrape_gold_price(html=SAMPLE_HTML)
    pt = result["pt_scrap"]
    assert pt["Pt1000"] == "11,148"
    assert pt["Pt900"] == "10,194"
    assert pt["Pt850"] == "9,620"
    assert len(pt) == 4


def test_scrape_silver_scrap_prices():
    """銀スクラップ価格（Sv1000/Sv925）を正しく抽出できる"""
    result = scrape_gold_price(html=SAMPLE_HTML)
    sv = result["silver_scrap"]
    assert sv["Sv1000"] == "387"
    assert sv["Sv925"] == "348"
    assert len(sv) == 2


def test_scrape_simple_html_has_empty_scrap():
    """スクラップセクションがないHTMLでは空dictが返る"""
    result = scrape_gold_price(html=SIMPLE_HTML)
    assert result["gold_scrap"] == {}
    assert result["pt_scrap"] == {}
    assert result["silver_scrap"] == {}


def test_scrape_published_prices():
    """自社サイトのテーブルから金属6種の価格を抽出できる（金貨は除外）"""
    result = scrape_published_price(html=PUBLISHED_HTML)
    prices = result["prices"]
    assert prices["K24"] == "24,190"
    assert prices["K18"] == "18,010"
    assert prices["K14"] == "13,030"
    assert prices["Pt1000"] == "9,710"
    assert prices["Pt900"] == "8,730"
    assert prices["Pt850"] == "8,200"
    # 金貨行(天皇陛下…)やK22は含まれない
    assert "K22" not in prices
    assert len(prices) == 6


def test_scrape_published_date():
    """日付を 'YYYY年MM月DD日' 形式で抽出できる"""
    result = scrape_published_price(html=PUBLISHED_HTML)
    assert result["date"] == "2026年06月07日"


def test_scrape_published_raises_without_wrap():
    """価格テーブルが無いHTMLでは ValueError を raise する"""
    with pytest.raises(ValueError, match="買取価格テーブルが見つかりません"):
        scrape_published_price(html="<html><body>なし</body></html>")


def test_scrape_published_raises_without_args():
    with pytest.raises(ValueError, match="url or html must be provided"):
        scrape_published_price()


@pytest.mark.slow
def test_scrape_gold_price_real_site():
    """実サイトから金価格を取得できる（要ネット接続）"""
    result = scrape_gold_price(url="https://www.net-japan.co.jp/precious_metal_partner/")
    assert "retail_price" in result
    assert "date" in result
    assert "gold_scrap" in result
    assert "pt_scrap" in result
    assert "silver_scrap" in result
    # 価格はカンマ区切りの数値形式であることを確認
    import re
    assert re.match(r"[\d,]+", result["retail_price"]), f"価格の形式が不正: {result['retail_price']}"
    assert "K18" in result["gold_scrap"]
    assert "Pt900" in result["pt_scrap"]
    print(f"\n取得結果: {result}")
