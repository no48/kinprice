from datetime import date

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/business.manage"]


def get_service(credentials_path: str):
    """Google Business Profile APIのサービスオブジェクトを取得する。"""
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    return build("mybusinessbusinessinformation", "v1", credentials=credentials)


def create_post(
    service,
    account_id: str,
    location_id: str,
    retail_price: str,
    purchase_price: str,
    price_date: str,
) -> dict:
    """Googleビジネスプロフィールに金価格の投稿を作成する。"""
    summary = (
        f"【{price_date} 金価格】\n"
        f"小売価格: {retail_price} 円/g\n"
        f"買取価格: {purchase_price} 円/g"
    )

    post_body = {
        "languageCode": "ja",
        "summary": summary,
        "topicType": "STANDARD",
    }

    parent = f"{account_id}/{location_id}"

    try:
        result = (
            service.accounts()
            .locations()
            .localPosts()
            .create(parent=parent, body=post_body)
            .execute()
        )
        return {
            "success": True,
            "message": "Googleビジネスプロフィールに投稿しました",
            "post_name": result.get("name", ""),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Google投稿エラー: {str(e)}",
        }


def delete_todays_posts(
    service,
    account_id: str,
    location_id: str,
) -> int:
    """当日の投稿を全て削除する。"""
    parent = f"{account_id}/{location_id}"
    today_str = date.today().isoformat()
    deleted_count = 0

    try:
        response = (
            service.accounts()
            .locations()
            .localPosts()
            .list(parent=parent)
            .execute()
        )
        posts = response.get("localPosts", [])

        for post in posts:
            create_time = post.get("createTime", "")
            if create_time.startswith(today_str):
                post_name = post["name"]
                service.accounts().locations().localPosts().delete(
                    name=post_name
                ).execute()
                deleted_count += 1
    except Exception:
        pass

    return deleted_count
