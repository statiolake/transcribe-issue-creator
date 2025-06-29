# Transcribe Issue Creator

朝会の文字起こしから議事録を自動生成し、GitHub の Issue を作成するツールです。

## 機能

- 🎤 **音声文字起こし**: Amazon Transcribe を使用したリアルタイム音声認識
- 📝 **議事録自動生成**: Claude を使用した AI 議事録生成
- 📋 **タスク抽出**: 会話から Issue 作成用のタスクを自動抽出
- ✏️ **Issue 編集**: 作成前にエディタで Issue を編集可能
- 👥 **担当者指定**: 自動検出または手動で担当者を指定
- 🏷️ **ラベル付け**: AI による自動ラベル推論または手動でのラベル設定
- 📊 **プロジェクト連携**: GitHub プロジェクトへの自動追加
- ⚙️ **カスタム指示**: `.custom-instructions` ファイルで AI の動作をカスタマイズ

## 必要な環境

- Python 3.10 以上
- [uv](https://docs.astral.sh/uv/getting-started/installation/) のインストール
- [GitHub CLI](https://cli.github.com/) のインストールと認証
- AWS Bedrock、Amazon Transcribe が使える AWS アカウントへのアクセス権限
- **portaudio** (pyaudio の依存関係のため必須):
  - macOS: `brew install portaudio`
  - Ubuntu/Debian: `sudo apt install portaudio19-dev`
  - Windows: 通常は追加設定が不要
  - WSL: `sudo apt install portaudio19-dev` (ただし、マイクアクセスは困難)
- タスク化した Issue を保存する GitHub のリポジトリ
  - 実行時に --repo オプションで指定します。

## インストールと実行方法

### オプション 1: uvx で直接実行

インストール不要で GitHub から直接実行できます。

```bash
# 環境変数を設定
export AWS_PROFILE=your-profile-name
export AWS_DEFAULT_REGION=ap-northeast-1

# GitHub から直接実行
# マイクロフォンから音声入力
uvx --from git+https://github.com/statiolake/transcribe-issue-creator transcribe-issue-creator --repo owner/repository

# プロジェクトを指定してすべてのIssueを同じプロジェクトに紐づけ
uvx --from git+https://github.com/statiolake/transcribe-issue-creator transcribe-issue-creator --repo owner/repository --project "Sprint 2024-Q1"

# テキストファイルから入力 (すでに別で文字起こしをした場合や WSL 利用時など)
cat meeting_notes.txt | uvx --from git+https://github.com/statiolake/transcribe-issue-creator transcribe-issue-creator --repo owner/repository --project "Sprint 2024-Q1"
```

### オプション 2: uv tool でインストール

グローバルにインストールして普通のコマンドのように実行できます。繰り返し使う場合はこうしてしまっても便利です。

```bash
# インストール
uv tool install git+https://github.com/statiolake/transcribe-issue-creator

# 環境変数を設定
export AWS_PROFILE=your-profile-name
export AWS_DEFAULT_REGION=ap-northeast-1

# 実行
# マイクロフォンから音声入力
transcribe-issue-creator --repo owner/repository

# プロジェクトを指定してすべてのIssueを同じプロジェクトに紐づけ
transcribe-issue-creator --repo owner/repository --project "Sprint 2024-Q1"

# テキストファイルから入力 (すでに別で文字起こしをした場合や WSL 利用時など)
cat meeting_notes.txt | transcribe-issue-creator --repo owner/repository --project "Sprint 2024-Q1"
```

## ツールの動作の流れ

### コマンドライン引数

- `--repo <owner/repository>` (必須): タスクを保存する GitHub リポジトリを指定します。
- `--project <project-name>`: 作成する Issue を指定のプロジェクトに紐づけます。指定がなければプロジェクトには追加しません。

### 音声入力

標準入力から文字列が渡されなかった場合は、音声入力モードが開始します。
マイクからの音声をリアルタイムで文字起こしします。

1. プログラムを実行すると音声入力が開始されます。
2. 話した内容がリアルタイムで文字起こしされます。
3. `Ctrl+D` を押して録音を終了します。

### Issue の編集

標準入力または文字起こしの内容をもとに、AI が議事録を生成し、タスク化すべき内容を抽出します。
抽出されたタスクは自動的にエディタで開かれ、登録前に編集することができます。

```markdown
# 【今日まで】API テストの完了 @statiolake

## 背景

- 田中さんの API 実装について

## 担当者

- statiolake

## やること

- API 修正のテストを完了する

---

# 【明日まで】新機能設計のレビュー

## 背景

- 新機能の設計について

## やること

- 設計書をレビューする
```

#### エディタでの編集方法

- **Issue の削除**: 不要な Issue があれば、全体を削除してしまえば登録されることはありません。逆に拾われなかったタスクを追加することもできます。
- **担当者指定**: タイトル末尾に `@ユーザー名` を追加すると GitHub の Assignee として扱われます (例: `@statiolake`) 。
- **ラベル設定**: タイトル末尾に `<[ラベル名]>` を追加すると GitHub のラベルとして扱われます (例: `<[バグ修正]> <[緊急]>`) 。
- **内容編集**: タイトルや本文を自由に修正できます。
- **区切り**: Issue は `---` で区切られます。

**編集時のタイトル例:**
```
【5/23 まで】佐藤さんからの問い合わせ対応 @dev-tanaka @sato-gh <[問い合わせ対応]> <[重要度高]>
```

## カスタム指示

`.custom-instructions` ファイルを作成して AI の動作をカスタマイズできます。
特に、チームのメンバー、プロジェクト名、ラベル付けルールはここで指定するとよいです。

### 基本的な設定例

```
# .custom-instructions の例
- チームメンバー: @alice (フロントエンド)、@bob (バックエンド)、@charlie (インフラ)
- 締切形式: 社内タスクには「とりあえず」を付ける
```

### ラベル付けの設定

**重要**: デフォルトでは AI はラベルを自動付与しません。`.custom-instructions` で明示的に指示した場合のみ、AI がラベルを推論します。

```
# ラベル付けルールの例
- バグ関連のタスクには "バグ修正" ラベルを付ける
- 新機能開発には "新機能" ラベルを付ける
- 緊急度の高いタスクには "緊急" ラベルを付ける
- インフラ関連作業には "インフラ" ラベルを付ける
- ドキュメント作成には "ドキュメント" ラベルを付ける
- 優先度に応じて "高優先度"、"中優先度"、"低優先度" ラベルを付ける
```

この内容は自動的に AI プロンプトに追加され、より適切な Issue 生成とラベル付けが行われます。

## 環境変数

```bash
# AWS 設定 (必須)
export AWS_PROFILE=your-profile-name
export AWS_DEFAULT_REGION=ap-northeast-1

# エディタの指定 (オプショナル)
# デフォルトでは nvim です。
# 例: VS Code を利用する場合
export EDITOR="code -w"
```

## 出力例

### 議事録 (Slack 用)

```
- メンバー A の進捗は順調で、API の実装が 80% 完了している
- 新機能 X の設計方針について議論し、マイクロサービス化で合意
- パフォーマンス問題が発生しており、データベースクエリの最適化が必要
```

### GitHub Issues

作成される Issue には以下が自動的に含まれます:

- **タイトル**: 締切付きの明確なタイトル
- **本文**: 構造化された内容 (背景、担当者、やること)
- **担当者**: 指定された担当者
- **ラベル**: AI が推論したラベルまたは手動で設定したラベル
- **プロジェクト**: 指定されたプロジェクトへの自動追加

## トラブルシューティング

### WSL 環境での音声入力について

WSL ではマイクアクセスが困難です。Windows 側に pulseaudio サーバーをインストールし、TCP 経由で接続するように Windows / WSL 双方の pulseaudio を設定する必要があります。
設定が複雑なため、基本的には Windows ネイティブまたは別の文字起こし (Notion 等) を利用したうえで標準入力からテキストを渡す方法を推奨します。

## 開発環境セットアップ

開発者向けの詳細なセットアップ手順:

```bash
# プロジェクトをクローン
git clone https://github.com/statiolake/transcribe-issue-creator
cd transcribe-issue-creator

# 依存関係をインストール
uv sync

# 開発用依存関係もインストール
uv sync --group dev

# 開発モードで実行
uv run python src/transcribe_issue_creator/main.py --repo owner/repository

# プロジェクトを指定して実行
uv run python src/transcribe_issue_creator/main.py --repo owner/repository --project "Sprint 2024-Q1"

# 型チェック
uv run mypy src/transcribe_issue_creator/

# リンティング
uv run ruff check src/transcribe_issue_creator/
```

## ライセンス

このプロジェクトは [MIT ライセンス](LICENSE) の下で公開されています。
