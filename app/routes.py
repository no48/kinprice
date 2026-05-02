import re
from flask import Blueprint, current_app, jsonify, render_template, request
from app.auth import protect
from app.scraper import scrape_gold_price
from app.margins import compute_adjusted
from app.wordpress import update_gold_page, today_jst_ja, update_date_only_on_wp

bp = Blueprint("main", __name__)
protect(bp)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/fetch", methods=["POST"])
def fetch_price():
    try:
        url = current_app.config["GOLD_SOURCE_URL"]
        raw = scrape_gold_price(url=url)
        adjusted = compute_adjusted(raw)
        return jsonify({
            "date": today_jst_ja(),
            "reference": {
                "K24":    raw["retail_price"],
                "K22":    raw["gold_scrap"]["K22"],
                "K18":    raw["gold_scrap"]["K18"],
                "K14":    raw["gold_scrap"]["K14"],
                "Pt1000": raw["pt_scrap"]["Pt1000"],
                "Pt900":  raw["pt_scrap"]["Pt900"],
                "Pt850":  raw["pt_scrap"]["Pt850"],
            },
            "adjusted": adjusted,
            "source_url": url,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/upload", methods=["POST"])
def upload_price():
    try:
        data = request.get_json(silent=True) or {}
        price_date = data.get("date", "")
        post_to_wp = data.get("post_to_wp", True)

        gold_scrap = data.get("gold_scrap", {}) or {}
        pt_scrap = data.get("pt_scrap", {}) or {}

        price_pattern = re.compile(r"^[\d,]+$")
        for key, val in list(gold_scrap.items()) + list(pt_scrap.items()):
            if not price_pattern.match(str(val)):
                return jsonify({"error": f"{key} の価格形式が不正です: '{val}'"}), 400

        date_pattern = re.compile(r"^[\d/:\s\u4e00-\u9fff年月日]+$")
        if price_date and not date_pattern.match(price_date):
            return jsonify({"error": "日付の形式が不正です"}), 400

        results = {}

        if post_to_wp:
            wp_result = update_gold_page(
                site_url=current_app.config["WP_SITE_URL"],
                username=current_app.config["WP_USERNAME"],
                app_password=current_app.config["WP_APP_PASSWORD"],
                page_id=current_app.config["WP_PAGE_ID"],
                gold_scrap=gold_scrap,
                pt_scrap=pt_scrap,
            )
            results["wordpress"] = wp_result

        k18_price = gold_scrap.get("K18", "")
        gbp_text = f"{price_date}本日K18/1g  {k18_price}円でお買い取りしております。"
        results["gbp_text"] = gbp_text
        results["gbp_search_url"] = current_app.config["GBP_SEARCH_URL"]
        results["source_url"] = current_app.config["GOLD_SOURCE_URL"]

        return jsonify(results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"サーバーエラー: {type(e).__name__}: {str(e)}"}), 500
