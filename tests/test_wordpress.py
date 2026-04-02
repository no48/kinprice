from unittest.mock import patch, MagicMock
from app.wordpress import update_gold_page


def test_update_gold_page_sends_correct_request():
    """WordPress APIに正しいリクエストを送信する"""
    with patch("app.wordpress.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "link": "https://example.com/gold"}
        mock_post.return_value = mock_response

        result = update_gold_page(
            site_url="https://example.com",
            username="admin",
            app_password="test-pass",
            page_id=123,
            retail_price="14,589",
            purchase_price="14,200",
            price_date="2026-04-02",
        )

        assert result["success"] is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/wp-json/wp/v2/pages/123" in call_args[0][0]


def test_update_gold_page_handles_api_error():
    """WordPress APIエラー時にエラー情報を返す"""
    with patch("app.wordpress.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")
        mock_post.return_value = mock_response

        result = update_gold_page(
            site_url="https://example.com",
            username="admin",
            app_password="wrong-pass",
            page_id=123,
            retail_price="14,589",
            purchase_price="14,200",
            price_date="2026-04-02",
        )

        assert result["success"] is False
        assert "error" in result
