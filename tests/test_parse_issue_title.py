"""Test cases for parse_issue_title function"""

import pytest
from transcribe_issue_creator.title_parser import parse_issue_title


class TestParseIssueTitle:
    """Test cases for parse_issue_title function"""

    def test_basic_parsing_with_all_elements(self):
        """基本的なパース処理（タイトル、アサイニー、ラベル全て含む）"""
        raw_title = "【5/23 まで】佐藤さんからの問い合わせ対応 @dev-tanaka @sato-gh <[問い合わせ対応]> <[重要度高]>"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "【5/23 まで】佐藤さんからの問い合わせ対応"
        assert assignees == ["dev-tanaka", "sato-gh"]
        assert labels == ["問い合わせ対応", "重要度高"]

    def test_parsing_with_different_order(self):
        """要素の順番が異なる場合のパース処理"""
        raw_title = "@dev-tanaka 【5/23 まで】佐藤さんからの問い合わせ対応 <[問い合わせ対応]> @sato-gh <[重要度高]>"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "【5/23 まで】佐藤さんからの問い合わせ対応"
        assert assignees == ["dev-tanaka", "sato-gh"]
        assert labels == ["問い合わせ対応", "重要度高"]

    def test_parsing_title_only(self):
        """タイトルのみの場合"""
        raw_title = "【5/23 まで】佐藤さんからの問い合わせ対応"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "【5/23 まで】佐藤さんからの問い合わせ対応"
        assert assignees == []
        assert labels == []

    def test_parsing_with_only_assignees(self):
        """アサイニーのみ含む場合"""
        raw_title = "【5/23 まで】佐藤さんからの問い合わせ対応 @dev-tanaka @sato-gh"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "【5/23 まで】佐藤さんからの問い合わせ対応"
        assert assignees == ["dev-tanaka", "sato-gh"]
        assert labels == []

    def test_parsing_with_only_labels(self):
        """ラベルのみ含む場合"""
        raw_title = "【5/23 まで】佐藤さんからの問い合わせ対応 <[問い合わせ対応]> <[重要度高]>"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "【5/23 まで】佐藤さんからの問い合わせ対応"
        assert assignees == []
        assert labels == ["問い合わせ対応", "重要度高"]

    def test_parsing_with_single_assignee(self):
        """単一のアサイニー"""
        raw_title = "【5/23 まで】佐藤さんからの問い合わせ対応 @dev-tanaka"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "【5/23 まで】佐藤さんからの問い合わせ対応"
        assert assignees == ["dev-tanaka"]
        assert labels == []

    def test_parsing_with_single_label(self):
        """単一のラベル"""
        raw_title = "【5/23 まで】佐藤さんからの問い合わせ対応 <[問い合わせ対応]>"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "【5/23 まで】佐藤さんからの問い合わせ対応"
        assert assignees == []
        assert labels == ["問い合わせ対応"]

    def test_parsing_with_hyphens_in_username(self):
        """ユーザー名にハイフンが含まれる場合"""
        raw_title = "タスク @user-name @test-user-123"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "タスク"
        assert assignees == ["user-name", "test-user-123"]
        assert labels == []

    def test_parsing_with_spaces_around_elements(self):
        """要素の周りに余分な空白がある場合"""
        raw_title = "  タスク   @user1   <[label1]>   @user2   <[label2]>  "
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "タスク"
        assert assignees == ["user1", "user2"]
        assert labels == ["label1", "label2"]

    def test_parsing_with_empty_brackets(self):
        """空のブラケットがある場合（無効なラベル）"""
        raw_title = "タスク @user1 <[]> <[valid-label]>"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "タスク"
        assert assignees == ["user1"]
        assert labels == ["valid-label"]  # 空のブラケットは無視される

    def test_parsing_with_complex_title(self):
        """複雑なタイトルの場合"""
        raw_title = "【緊急】データベース接続エラーの調査と修正 @backend-team @infra-lead <[バグ修正]> <[緊急]> <[データベース]>"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "【緊急】データベース接続エラーの調査と修正"
        assert assignees == ["backend-team", "infra-lead"]
        assert labels == ["バグ修正", "緊急", "データベース"]

    def test_parsing_with_nested_brackets_in_title(self):
        """タイトル内に通常のブラケットが含まれる場合（誤爆防止テスト）"""
        raw_title = "【5/23】API [v2] の実装 @dev <[新機能]>"
        title, assignees, labels = parse_issue_title(raw_title)
        
        assert title == "【5/23】API [v2] の実装"
        assert assignees == ["dev"]
        assert labels == ["新機能"]