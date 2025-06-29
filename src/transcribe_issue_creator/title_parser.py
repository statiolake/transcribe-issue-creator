"""Title parsing utilities for GitHub Issues"""

import re


def parse_issue_title(raw_title: str) -> tuple[str, list[str], list[str]]:
    """タイトルからアサイニーとラベルを抽出し、クリーンなタイトルを返す
    
    Args:
        raw_title: パース対象の生タイトル
        
    Returns:
        tuple[str, list[str], list[str]]: (clean_title, assignees, labels)
        
    Examples:
        >>> parse_issue_title("【5/23 まで】佐藤さんからの問い合わせ対応 @dev-tanaka @sato-gh <[問い合わせ対応]> <[重要度高]>")
        ("【5/23 まで】佐藤さんからの問い合わせ対応", ["dev-tanaka", "sato-gh"], ["問い合わせ対応", "重要度高"])
        
        >>> parse_issue_title("@dev-tanaka 【5/23 まで】佐藤さんからの問い合わせ対応 <[問い合わせ対応]> @sato-gh <[重要度高]>")
        ("【5/23 まで】佐藤さんからの問い合わせ対応", ["dev-tanaka", "sato-gh"], ["問い合わせ対応", "重要度高"])
    """
    # @username を抽出
    assignee_matches = re.findall(r"@([\w-]+)", raw_title)
    
    # <[label]> を抽出
    label_matches = re.findall(r"<\[([^\]]+)\]>", raw_title)
    
    # @username を除去
    clean_title = re.sub(r"\s*@[\w-]+\s*", " ", raw_title)
    
    # <[label]> を除去（空のブラケットも含む）
    clean_title = re.sub(r"\s*<\[[^\]]*\]>\s*", " ", clean_title)
    
    # 余分な空白を除去
    clean_title = re.sub(r"\s+", " ", clean_title).strip()
    
    return clean_title, assignee_matches, label_matches