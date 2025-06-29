"""Title parsing utilities for GitHub Issues"""

import re
from dataclasses import dataclass


@dataclass
class IssueTitle:
    """パースされたIssueタイトルの情報"""

    title: str
    assignees: list[str]
    labels: list[str]


def parse_issue_title(raw_title: str) -> IssueTitle:
    """タイトルからアサイニーとラベルを抽出し、パースされたタイトル情報を返す

    Args:
        raw_title: パース対象の生タイトル

    Returns:
        IssueTitle: パースされたタイトル情報

    Examples:
        >>> result = parse_issue_title("【5/23 まで】佐藤さんからの問い合わせ対応 @dev-tanaka @sato-gh <[問い合わせ対応]> <[重要度高]>")
        >>> result.title
        "【5/23 まで】佐藤さんからの問い合わせ対応"
        >>> result.assignees
        ["dev-tanaka", "sato-gh"]
        >>> result.labels
        ["問い合わせ対応", "重要度高"]
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

    return IssueTitle(
        title=clean_title,
        assignees=assignee_matches,
        labels=label_matches,
    )
