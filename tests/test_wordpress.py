from unittest.mock import patch, MagicMock
from app.wordpress import update_gold_page, today_jst_ja


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


def test_today_jst_ja_returns_japanese_date_format():
    """today_jst_ja() は 'YYYY年MM月DD日' 形式を返す。"""
    import re
    result = today_jst_ja()
    assert re.match(r"^\d{4}年\d{2}月\d{2}日$", result)


def test_update_gold_page_uses_provided_date():
    """page_date 引数で渡された日付がページ内容に反映される。"""
    with patch("app.wordpress.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "link": "https://example.com/gold"}
        mock_post.return_value = mock_response

        update_gold_page(
            site_url="https://example.com",
            username="admin",
            app_password="test-pass",
            page_id=123,
            gold_scrap={"K24": "25,000", "K18": "19,000", "K14": "14,000"},
            pt_scrap={"Pt1000": "11,000", "Pt900": "10,000", "Pt850": "9,000"},
            page_date="2026年05月02日",
        )

        body = mock_post.call_args_list[1].kwargs["json"]["content"]
        assert "2026年05月02日" in body


def test_update_gold_page_falls_back_to_today_when_no_date():
    """page_date が未指定なら today_jst_ja() を使う（後方互換）。"""
    with patch("app.wordpress.requests.post") as mock_post, \
         patch("app.wordpress.today_jst_ja", return_value="2026年12月31日"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "link": ""}
        mock_post.return_value = mock_response

        update_gold_page(
            site_url="https://example.com",
            username="admin",
            app_password="x",
            page_id=123,
            gold_scrap={"K18": "19,000"},
            pt_scrap={},
        )

        body = mock_post.call_args_list[1].kwargs["json"]["content"]
        assert "2026年12月31日" in body


from app.wordpress import update_date_only_on_wp


def test_update_date_only_replaces_date_in_existing_content():
    """既存ページのHTMLから日付だけを置換する。"""
    existing_html = '<p class="date">2026年04月20日    現在の買取金額</p>'
    with patch("app.wordpress.requests.get") as mock_get, \
         patch("app.wordpress.requests.post") as mock_post:
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {"content": {"raw": existing_html}}
        mock_get.return_value = mock_get_resp
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"link": "https://example.com/gold"}
        mock_post.return_value = mock_post_resp

        result = update_date_only_on_wp(
            site_url="https://example.com",
            username="admin",
            app_password="x",
            page_id=123,
            new_date="2026年05月02日",
        )

        assert result["success"] is True
        sent_body = mock_post.call_args.kwargs["json"]["content"]
        assert "2026年05月02日" in sent_body
        assert "2026年04月20日" not in sent_body


def test_update_date_only_returns_error_when_no_date_pattern():
    """既存ページに日付パターンが無い場合はエラーを返す（POSTしない）。"""
    with patch("app.wordpress.requests.get") as mock_get, \
         patch("app.wordpress.requests.post") as mock_post:
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {"content": {"raw": "<p>no date here</p>"}}
        mock_get.return_value = mock_get_resp

        result = update_date_only_on_wp(
            site_url="https://example.com",
            username="admin",
            app_password="x",
            page_id=123,
            new_date="2026年05月02日",
        )

        assert result["success"] is False
        assert "見つかりません" in result["error"]
        mock_post.assert_not_called()


def test_update_date_only_handles_api_error():
    """WP API GET失敗時にエラー情報を返す。"""
    with patch("app.wordpress.requests.get") as mock_get:
        mock_get_resp = MagicMock()
        mock_get_resp.raise_for_status.side_effect = Exception("Unauthorized")
        mock_get.return_value = mock_get_resp

        result = update_date_only_on_wp(
            site_url="https://example.com",
            username="admin",
            app_password="x",
            page_id=123,
            new_date="2026年05月02日",
        )
        assert result["success"] is False
        assert "error" in result
