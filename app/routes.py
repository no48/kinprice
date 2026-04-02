import re
from flask import Blueprint, current_app, jsonify, render_template, request
from app.scraper import scrape_gold_price
from app.wordpress import update_gold_page
from app.google_business import get_service, create_post, delete_todays_posts

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
    post_to_google = data.get("post_to_google", True)

    # Input validation: retail_price is required; purchase_price is optional
    price_pattern = re.compile(r"^[\d,]+$")
    if not price_pattern.match(retail_price):
        return jsonify({"error": "価格は数値のみ入力してください"}), 400
    if purchase_price and not price_pattern.match(purchase_price):
        return jsonify({"error": "価格は数値のみ入力してください"}), 400
    # If purchase_price is omitted, default to retail_price
    if not purchase_price:
        purchase_price = retail_price

    # Validate date to prevent XSS (allow digits, slash, colon, space only)
    date_pattern = re.compile(r"^[\d/:\s]+$")
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

    if post_to_google:
        try:
            service = get_service(current_app.config["GOOGLE_CREDENTIALS_PATH"])
            account_id = current_app.config["GOOGLE_ACCOUNT_ID"]
            location_id = current_app.config["GOOGLE_LOCATION_ID"]
            deleted = delete_todays_posts(service, account_id, location_id)
            google_result = create_post(
                service=service,
                account_id=account_id,
                location_id=location_id,
                retail_price=retail_price,
                purchase_price=purchase_price,
                price_date=price_date,
            )
            if deleted > 0:
                google_result["message"] += f"（既存{deleted}件を上書き）"
            results["google"] = google_result
        except Exception as e:
            results["google"] = {"success": False, "error": f"Google投稿エラー: {str(e)}"}

    return jsonify(results)
