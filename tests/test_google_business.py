from unittest.mock import patch, MagicMock
from app.google_business import create_post, delete_todays_posts


def test_create_post_sends_correct_request():
    """Google Business Profile APIに正しいリクエストを送信する"""
    mock_service = MagicMock()
    mock_create = mock_service.accounts().locations().localPosts().create
    mock_create.return_value.execute.return_value = {"name": "accounts/123/locations/456/localPosts/789"}

    result = create_post(
        service=mock_service,
        account_id="accounts/123",
        location_id="locations/456",
        retail_price="14,589",
        purchase_price="14,200",
        price_date="2026-04-02",
    )

    assert result["success"] is True
    mock_create.assert_called_once()


def test_create_post_handles_api_error():
    """Google APIエラー時にエラー情報を返す"""
    mock_service = MagicMock()
    mock_create = mock_service.accounts().locations().localPosts().create
    mock_create.return_value.execute.side_effect = Exception("API Error")

    result = create_post(
        service=mock_service,
        account_id="accounts/123",
        location_id="locations/456",
        retail_price="14,589",
        purchase_price="14,200",
        price_date="2026-04-02",
    )

    assert result["success"] is False
    assert "error" in result
