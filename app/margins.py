"""自店買取価格のマージン計算。"""

import json
import os
from pathlib import Path

# デフォルト値（margins.json が無い／壊れている時のフォールバック）
DEFAULT_MARGINS = {
    "K24":    170,
    "K22":    900,   # 自店K24から引く額（NJのK22は使わない）
    "K14":    400,
    "Pt1000": 200,
    "Pt900":  50,
    "Pt850":  80,
}

MARGIN_KEYS = list(DEFAULT_MARGINS.keys())


def get_margins_path() -> Path:
    """マージン設定ファイルのパス。MARGINS_FILE_PATH 環境変数で上書き可能。"""
    override = os.environ.get("MARGINS_FILE_PATH")
    if override:
        return Path(override)
    return Path(__file__).parent.parent / "data" / "margins.json"


def load_margins() -> dict:
    """JSONファイルからマージン設定を読み込む。失敗時はデフォルトを返す。"""
    path = get_margins_path()
    if not path.exists():
        return DEFAULT_MARGINS.copy()
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return DEFAULT_MARGINS.copy()

    merged = DEFAULT_MARGINS.copy()
    for k in MARGIN_KEYS:
        v = data.get(k)
        if isinstance(v, int) and v >= 0:
            merged[k] = v
    return merged


def save_margins(margins: dict) -> None:
    """マージン設定をJSONファイルに保存する。"""
    filtered = {}
    for k in MARGIN_KEYS:
        v = margins.get(k)
        if not isinstance(v, int) or v < 0:
            raise ValueError(f"{k} は0以上の整数で指定してください: {v!r}")
        filtered[k] = v

    path = get_margins_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)


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
    margins = load_margins()

    nj_k24    = _to_int(raw["retail_price"])
    nj_k18    = raw["gold_scrap"]["K18"]
    nj_k14    = _to_int(raw["gold_scrap"]["K14"])
    nj_pt1000 = _to_int(raw["pt_scrap"]["Pt1000"])
    nj_pt900  = _to_int(raw["pt_scrap"]["Pt900"])
    nj_pt850  = _to_int(raw["pt_scrap"]["Pt850"])

    k24 = floor10(nj_k24) - margins["K24"]
    k22 = floor10(k24 - margins["K22"])

    return {
        "K24":    _fmt(k24),
        "K22":    _fmt(k22),
        "K18":    nj_k18,
        "K14":    _fmt(floor10(nj_k14) - margins["K14"]),
        "Pt1000": _fmt(floor10(nj_pt1000) - margins["Pt1000"]),
        "Pt900":  _fmt(floor10(nj_pt900)  - margins["Pt900"]),
        "Pt850":  _fmt(floor10(nj_pt850)  - margins["Pt850"]),
    }
