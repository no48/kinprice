"""app/margins.py の単体テスト。"""
import pytest
from app.margins import floor10, compute_adjusted


def test_floor10_truncates_ones_digit():
    assert floor10(25_614) == 25_610
    assert floor10(25_619) == 25_610
    assert floor10(25_610) == 25_610
    assert floor10(0) == 0
    assert floor10(9) == 0


def test_compute_adjusted_k24():
    """K24 = floor10(NJ K24) - 170"""
    raw = _raw_with(retail_price="26,352")
    assert compute_adjusted(raw)["K24"] == "26,180"


def test_compute_adjusted_k22():
    """K22 = floor10(自店K24 - 900)。NJのK22は使わない。"""
    raw = _raw_with(retail_price="26,352", k22="99,999")  # K22は無視される
    result = compute_adjusted(raw)
    # K24自店=26,180 → 26,180-900=25,280 → floor10=25,280
    assert result["K22"] == "25,280"


def test_compute_adjusted_k18_passthrough():
    """K18 はNJ値をそのまま返す（マージン適用なし）。"""
    raw = _raw_with(k18="19,553")
    assert compute_adjusted(raw)["K18"] == "19,553"


def test_compute_adjusted_k14():
    """K14 = floor10(NJ K14) - 400"""
    raw = _raw_with(k14="14,494")
    # 14,490 - 400 = 14,090
    assert compute_adjusted(raw)["K14"] == "14,090"


def test_compute_adjusted_pt1000():
    raw = _raw_with(pt1000="10,849")
    # 10,840 - 200 = 10,640
    assert compute_adjusted(raw)["Pt1000"] == "10,640"


def test_compute_adjusted_pt900():
    raw = _raw_with(pt900="9,921")
    # 9,920 - 50 = 9,870
    assert compute_adjusted(raw)["Pt900"] == "9,870"


def test_compute_adjusted_pt850():
    raw = _raw_with(pt850="9,362")
    # 9,360 - 80 = 9,280
    assert compute_adjusted(raw)["Pt850"] == "9,280"


def test_compute_adjusted_full_example():
    """仕様書の総合例（2026/04/24時点のNJ値）。"""
    raw = {
        "retail_price": "26,352",
        "gold_scrap": {"K24": "25,614", "K22": "23,216", "K18": "19,553", "K14": "14,494"},
        "pt_scrap":   {"Pt1000": "10,849", "Pt950": "10,290", "Pt900": "9,921", "Pt850": "9,362"},
    }
    result = compute_adjusted(raw)
    assert result == {
        "K24":    "26,180",
        "K22":    "25,280",
        "K18":    "19,553",
        "K14":    "14,090",
        "Pt1000": "10,640",
        "Pt900":  "9,870",
        "Pt850":  "9,280",
    }


def _raw_with(retail_price="26,352", k22="23,216", k18="19,553", k14="14,494",
              pt1000="10,849", pt900="9,921", pt850="9,362"):
    return {
        "retail_price": retail_price,
        "gold_scrap": {"K24": "0", "K22": k22, "K18": k18, "K14": k14},
        "pt_scrap":   {"Pt1000": pt1000, "Pt900": pt900, "Pt850": pt850},
    }
