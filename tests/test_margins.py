"""app/margins.py の単体テスト。"""
import json
import pytest
from app.margins import floor10, compute_adjusted, load_margins, save_margins, DEFAULT_MARGINS


@pytest.fixture(autouse=True)
def isolate_margins_file(tmp_path, monkeypatch):
    """各テストでmargins.jsonを一時ファイルに隔離する。"""
    monkeypatch.setenv("MARGINS_FILE_PATH", str(tmp_path / "margins.json"))


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


def test_compute_adjusted_k18_is_raw_value():
    """K18はネットジャパンの生値そのまま（丸めなし）。19,553 → 19,553。"""
    raw = _raw_with(k18="19,553")
    assert compute_adjusted(raw)["K18"] == "19,553"


def test_compute_adjusted_k18_ignores_margin():
    """K18は生値固定なので、マージン設定があっても無視される。"""
    save_margins({"K24": 0, "K22": 0, "K18": 100, "K14": 0, "Pt1000": 0, "Pt900": 0, "Pt850": 0})
    raw = _raw_with(k18="19,553")
    # マージン100は効かず、生値のまま
    assert compute_adjusted(raw)["K18"] == "19,553"


def test_compute_adjusted_k14():
    """K14 = floor10(NJ K14) - 400"""
    raw = _raw_with(k14="14,494")
    # 14,490 - 400 = 14,090
    assert compute_adjusted(raw)["K14"] == "14,090"


def test_compute_adjusted_pt1000():
    """Pt1000 = floor10(NJ Pt小売価格) - 200。NJのPt1000スクラップ値は使わない。"""
    raw = _raw_with(pt_retail_price="11,200", pt1000="99,999")  # Pt1000スクラップは無視される
    # floor10(11,200) - 200 = 11,000
    assert compute_adjusted(raw)["Pt1000"] == "11,000"


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
        "pt_retail_price": "11,200",
        "gold_scrap": {"K24": "25,614", "K22": "23,216", "K18": "19,553", "K14": "14,494"},
        "pt_scrap":   {"Pt1000": "10,849", "Pt950": "10,290", "Pt900": "9,921", "Pt850": "9,362"},
    }
    result = compute_adjusted(raw)
    assert result == {
        "K24":    "26,180",
        "K22":    "25,280",
        "K18":    "19,553",
        "K14":    "14,090",
        "Pt1000": "11,000",
        "Pt900":  "9,870",
        "Pt850":  "9,280",
    }


def _raw_with(retail_price="26,352", pt_retail_price="11,200",
              k22="23,216", k18="19,553", k14="14,494",
              pt1000="10,849", pt900="9,921", pt850="9,362"):
    return {
        "retail_price": retail_price,
        "pt_retail_price": pt_retail_price,
        "gold_scrap": {"K24": "0", "K22": k22, "K18": k18, "K14": k14},
        "pt_scrap":   {"Pt1000": pt1000, "Pt900": pt900, "Pt850": pt850},
    }


# ---------------------------------------------------------------------------
# load_margins / save_margins
# ---------------------------------------------------------------------------

def test_load_margins_returns_defaults_when_file_missing():
    assert load_margins() == DEFAULT_MARGINS


def test_load_margins_reads_saved_values(tmp_path, monkeypatch):
    save_margins({"K24": 200, "K22": 1000, "K18": 50, "K14": 500, "Pt1000": 250, "Pt900": 60, "Pt850": 90})
    loaded = load_margins()
    assert loaded["K24"] == 200
    assert loaded["K22"] == 1000
    assert loaded["K18"] == 50
    assert loaded["K14"] == 500


def test_load_margins_returns_defaults_when_file_malformed(tmp_path, monkeypatch):
    import os
    path = os.environ["MARGINS_FILE_PATH"]
    with open(path, "w") as f:
        f.write("not valid json {")
    assert load_margins() == DEFAULT_MARGINS


def test_load_margins_falls_back_for_missing_keys(tmp_path):
    """ファイルに一部キーしか無い場合、欠落分はデフォルトを使う。"""
    save_margins({"K24": 999, "K22": 0, "K18": 0, "K14": 0, "Pt1000": 0, "Pt900": 0, "Pt850": 0})
    loaded = load_margins()
    assert loaded["K24"] == 999
    # その他はそのまま読まれる
    assert loaded["K22"] == 0


def test_save_margins_rejects_non_integer():
    with pytest.raises(ValueError):
        save_margins({"K24": "abc", "K22": 0, "K18": 0, "K14": 0, "Pt1000": 0, "Pt900": 0, "Pt850": 0})


def test_save_margins_rejects_negative():
    with pytest.raises(ValueError):
        save_margins({"K24": -1, "K22": 0, "K18": 0, "K14": 0, "Pt1000": 0, "Pt900": 0, "Pt850": 0})


def test_compute_adjusted_uses_loaded_margins():
    """save_margins後、compute_adjustedは新しい値を使う。"""
    save_margins({"K24": 0, "K22": 0, "K18": 0, "K14": 0, "Pt1000": 0, "Pt900": 0, "Pt850": 0})
    raw = _raw_with(retail_price="26,352")
    # マージン全部0なので K24 = floor10(26,352) - 0 = 26,350
    assert compute_adjusted(raw)["K24"] == "26,350"
