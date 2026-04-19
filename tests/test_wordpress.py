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
            gold_scrap={"K24": "25,000", "K18": "19,000", "K14": "14,000"},
            pt_scrap={"Pt1000": "11,000", "Pt900": "10,000", "Pt850": "9,000"},
        )

        assert result["success"] is True
        assert mock_post.call_count == 2  # clear + write
        call_args = mock_post.call_args_list[0]
        assert "/wp-json/wp/v2/pages/123" in call_args[0][0]
        # 最初のリクエストは空contentでクリア
        assert mock_post.call_args_list[0].kwargs["json"] == {"content": ""}
        # 2回目は新しいcontent
        assert mock_post.call_args_list[1].kwargs["json"]["content"] != ""


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
            gold_scrap={"K24": "25,000", "K18": "19,000", "K14": "14,000"},
            pt_scrap={"Pt1000": "11,000", "Pt900": "10,000", "Pt850": "9,000"},
        )

        assert result["success"] is False
        assert "error" in result
