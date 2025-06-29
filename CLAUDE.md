# Transcribe Issue Creator - Claude Development Guide

## プロジェクト概要

朝会の文字起こしから議事録を自動生成し、GitHub Issues を作成するPythonツールです。

**主要機能:**
- Amazon Transcribe を使用したリアルタイム音声文字起こし
- Claude (AWS Bedrock) による議事録自動生成とタスク抽出
- GitHub Issues の自動作成（担当者、ラベル、プロジェクト対応）
- AI によるラベル推論（カスタム指示対応）
- エディタでの Issue 内容編集機能

## プロジェクト構造

```
src/transcribe_issue_creator/
├── __init__.py          # パッケージ初期化
├── main.py             # メインアプリケーション（CLI、音声処理、Issue作成）
└── title_parser.py     # Issue タイトルパース機能（IssueTitle dataclass）

tests/
├── __init__.py
└── test_parse_issue_title.py  # タイトルパース機能のテスト（12テストケース）

.github/workflows/
└── ci.yml              # CI/CD パイプライン（Python 3.10-3.12）

pyproject.toml          # 依存関係、taskipy設定、pytest設定
README.md              # ユーザー向けドキュメント
CLAUDE.md              # 開発者向けガイド（このファイル）
```

## 開発環境セットアップ

### 必要な環境
- Python 3.10 以上
- uv（依存関係管理）
- AWS アカウント（Bedrock、Transcribe アクセス）
- GitHub CLI
- portaudio19-dev（音声処理用）

### セットアップ手順

```bash
# リポジトリクローン
git clone https://github.com/statiolake/transcribe-issue-creator
cd transcribe-issue-creator

# 依存関係インストール
uv sync --all-extras --dev

# 動作確認
uv run transcribe-issue-creator --help
```

## コミットルール

### コミットメッセージ形式

```
<type>: <description>

[optional body]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### コミットタイプ
- `feat:` 新機能追加
- `fix:` バグ修正  
- `docs:` ドキュメント更新
- `refactor:` リファクタリング
- `test:` テスト追加・修正
- `chore:` その他（依存関係更新、設定変更など）

### 最近のコミット例
- `feat: replace tuple with IssueTitle dataclass and add CI`
- `feat: add taskipy for code quality automation`
- `feat: add comprehensive label support with AI inference`
- `feat: add Dev Container support`

## 品質管理

### 開発用コマンド

```bash
# コード品質チェック（ruff + mypy）
uv run task check

# コードフォーマット（ruff format + import整理）
uv run task format

# テスト実行
uv run pytest -v

# 全品質チェック実行
uv run task format && uv run task check && uv run pytest
```

### CI/CD

GitHub Actions で以下を自動実行：
- Python 3.10, 3.11, 3.12 でのマトリックステスト
- コード品質チェック（ruff check + mypy）
- テストスイート実行（pytest）
- パッケージビルド確認

## 主要な技術的詳細

### dataclass 設計

```python
@dataclass
class Task:
    """LLM が抽出するタスク情報"""
    title: str
    body: str
    deadline: str
    assignees: list[str]
    labels: list[str]

@dataclass  
class Issue:
    """GitHub Issue 作成用の情報"""
    title: str
    body: str
    assignees: list[str]
    labels: list[str]

@dataclass
class IssueTitle:
    """パースされたタイトル情報"""
    title: str
    assignees: list[str]
    labels: list[str]
```

### ラベル機能

- 手動指定: `<[ラベル名]>` 記法
- AI推論: `.custom-instructions` ファイルで設定
- パース処理: `title_parser.py` の `parse_issue_title` 関数

### プロンプト設計

- ベースプロンプト + カスタム指示の組み合わせ
- `build_system_prompt()` 関数で DRY 原則を実現
- 議事録生成とタスク抽出で異なるプロンプト使用

## 開発時の注意点

### 音声処理
- WSL環境ではマイクアクセスが困難
- 標準入力からのテキスト入力もサポート

### AWS設定
- AWS_PROFILE と AWS_DEFAULT_REGION の設定が必要
- Bedrock の Claude Sonnet 4 を使用

### テスト
- 12個のテストケースで IssueTitle パース機能をカバー
- 複雑なタイトル、空要素、順序違いなど多様なケースをテスト

### エラーハンドリング
- pyaudio 未インストール時の graceful fallback
- AWS 認証エラー時の適切なエラーメッセージ
- カスタム指示ファイル読み込みエラーの処理

## よくある開発タスク

### 新機能追加
1. feature ブランチ作成
2. 機能実装
3. テスト追加
4. `uv run task format && uv run task check` で品質確認
5. コミット（適切なメッセージで）
6. PR 作成

### バグ修正
1. 問題の再現テスト作成
2. 修正実装
3. テスト確認
4. 品質チェック実行
5. コミット

### 依存関係更新
1. `uv sync` で最新化
2. テスト実行で動作確認
3. CI 通過確認
4. `chore:` タイプでコミット

## パフォーマンス考慮事項

- Amazon Transcribe: リアルタイム処理でレスポンス重視
- Bedrock Claude: プロンプトサイズと応答時間のバランス
- GitHub CLI: 大量Issue作成時のレート制限注意

## セキュリティ

- AWS 認証情報はプロファイル使用（直接埋め込み禁止）
- カスタム指示ファイルはローカルのみ（リポジトリ非追跡）
- GitHub トークンは gh CLI で管理