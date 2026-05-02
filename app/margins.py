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
