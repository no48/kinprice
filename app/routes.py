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
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/upload", methods=["POST"])
def upload_price():
    data = request.get_json()
    retail_price = data.get("retail_price", "")
    purchase_price = data.get("purchase_price", "")
    price_date = data.get("date", "")
    post_to_wp = data.get("post_to_wp", True)

    price_pattern = re.compile(r"^[\d,]+$")
    if not price_pattern.match(retail_price):
        return jsonify({"error": "価格は数値のみ入力してください"}), 400
    if purchase_price and not price_pattern.match(purchase_price):
        return jsonify({"error": "価格は数値のみ入力してください"}), 400
    if not purchase_price:
        purchase_price = retail_price

    date_pattern = re.compile(r"^[\d/:\s\u4e00-\u9fff]+$")
    if price_date and not date_pattern.match(price_date):
        return jsonify({"error": "日付の形式が不正です"}), 400

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
        )
        results["wordpress"] = wp_result

    gbp_text = f"{price_date}本日K18/1g  {purchase_price}円でお買い取りしております。"
    results["gbp_text"] = gbp_text
    results["gbp_search_url"] = current_app.config["GBP_SEARCH_URL"]

    return jsonify(results)
