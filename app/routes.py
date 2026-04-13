import re
from flask import Blueprint, current_app, jsonify, render_template, request
from app.scraper import scrape_gold_price
from app.wordpress import update_gold_page

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/fetch", methods=["POST"])
def fetch_price():
    try:
        url = current_app.config["GOLD_SOURCE_URL"]
        result = scrape_gold_price(url=url)
        result["source_url"] = url
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/upload", methods=["POST"])
def upload_price():
    try:
        data = request.get_json(silent=True) or {}
        retail_price = (data.get("retail_price") or "").strip()
        purchase_price = (data.get("purchase_price") or "").strip()
        price_date = data.get("date", "")
        post_to_wp = data.get("post_to_wp", True)

        price_pattern = re.compile(r"^[\d,]+$")
        if not price_pattern.match(retail_price):
            return jsonify({"error": f"小売価格の形式が不正です: '{retail_price}'"}), 400
        if purchase_price and not price_pattern.match(purchase_price):
            return jsonify({"error": f"買取価格の形式が不正です: '{purchase_price}'"}), 400
        if not purchase_price:
            purchase_price = retail_price

        date_pattern = re.compile(r"^[\d/:\s\u4e00-\u9fff]+$")
        if price_date and not date_pattern.match(price_date):
            return jsonify({"error": "日付の形式が不正です"}), 400

        gold_scrap = data.get("gold_scrap", {}) or {}
        pt_scrap = data.get("pt_scrap", {}) or {}

        results = {}

        if post_to_wp:
            wp_result = update_gold_page(
                site_url=current_app.config["WP_SITE_URL"],
                username=current_app.config["WP_USERNAME"],
                app_password=current_app.config["WP_APP_PASSWORD"],
                page_id=current_app.config["WP_PAGE_ID"],
                retail_price=retail_price,
                purchase_price=purchase_price,
                price_date=price_date,
                gold_scrap=gold_scrap,
                pt_scrap=pt_scrap,
            )
            results["wordpress"] = wp_result

        k18_price = gold_scrap.get("K18", purchase_price)
        gbp_text = f"{price_date}本日K18/1g  {k18_price}円でお買い取りしております。"
        results["gbp_text"] = gbp_text
        results["gbp_search_url"] = current_app.config["GBP_SEARCH_URL"]
        results["source_url"] = current_app.config["GOLD_SOURCE_URL"]

        return jsonify(results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"サーバーエラー: {type(e).__name__}: {str(e)}"}), 500
