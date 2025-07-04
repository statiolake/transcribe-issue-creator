import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime

import boto3
import requests
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

from .title_parser import parse_issue_title

try:
    import pyaudio

    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False


@dataclass
class Task:
    """抽出されたタスク情報"""

    title: str
    body: str
    deadline: str
    assignees: list[str]
    labels: list[str]


@dataclass
class Issue:
    """GitHub Issue作成用の情報"""

    title: str
    body: str
    assignees: list[str]
    labels: list[str]


class TranscriptionHandler(TranscriptResultStreamHandler):
    def __init__(self, stream):
        super().__init__(stream)
        self.transcription_results = []

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if not result.is_partial:
                # 確定した文字起こし結果のみを処理
                for alt in result.alternatives or []:
                    self.transcription_results.append(alt.transcript)
                    # 確定した文字列を即座に出力（スペース付きで連結）
                    print(alt.transcript + " ", end="", flush=True)

    def get_final_transcript(self) -> str:
        """最終的な文字起こし結果を返す"""
        print()  # 最後に改行
        return " ".join(self.transcription_results)


async def get_input_text():
    """stdin からの入力またはマイクロフォンからの音声を取得"""
    # stdinにデータがパイプされているかチェック
    if not sys.stdin.isatty():
        print("stdinからテキストを読み込んでいます...")
        text = sys.stdin.read().strip()
        if text:
            print(f"入力テキスト: {text[:100]}{'...' if len(text) > 100 else ''}")
            return text
        else:
            print("stdinからの入力が空でした。")
            return ""

    # pyaudioが利用可能な場合は音声入力
    if PYAUDIO_AVAILABLE:
        return await transcribe_microphone()
    else:
        print(
            "エラー: pyaudioがインストールされておらず、stdinからの入力もありません。"
        )
        print("以下のいずれかの方法で入力してください:")
        print("1. echo 'テキスト' | python main.py")
        print("2. pyaudioをインストールしてマイクロフォンを使用")
        sys.exit(1)


async def transcribe_microphone():
    """マイクロフォンからの音声をリアルタイムで文字起こし"""
    print("🎤 音声入力を開始します...")
    print("💡 録音を終了するには Ctrl+D を押してください")
    print("─" * 60)

    # Amazon Transcribe Streaming クライアントを初期化
    client = TranscribeStreamingClient(region="ap-northeast-1")

    # ストリーミング文字起こしを開始
    stream = await client.start_stream_transcription(
        language_code="ja-JP",
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )

    handler = TranscriptionHandler(stream.output_stream)

    # PyAudioの設定
    CHUNK = 1024 * 8
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    audio = pyaudio.PyAudio()

    # 終了フラグ
    stop_recording = threading.Event()

    def wait_for_quit():
        """Ctrl+D (EOF) 入力を待機"""
        while not stop_recording.is_set():
            try:
                input()  # Ctrl+D でEOFError が発生
            except EOFError:
                stop_recording.set()
                break
            except Exception:
                break

    try:
        # マイクロフォンからの音声ストリームを開始
        audio_stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        # 別スレッドで終了キー監視開始
        quit_thread = threading.Thread(target=wait_for_quit, daemon=True)
        quit_thread.start()

        async def write_audio_chunks():
            """音声データをTranscribeに送信"""
            try:
                while not stop_recording.is_set():
                    data = audio_stream.read(CHUNK, exception_on_overflow=False)
                    await stream.input_stream.send_audio_event(audio_chunk=data)
                    await asyncio.sleep(0.01)
            except Exception as e:
                print(f"\n⚠️  音声入力エラー: {e}")
            finally:
                await stream.input_stream.end_stream()

        # 音声入力と文字起こし処理を並行実行
        await asyncio.gather(write_audio_chunks(), handler.handle_events())

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
    finally:
        # クリーンアップ
        stop_recording.set()
        if "audio_stream" in locals():
            audio_stream.stop_stream()
            audio_stream.close()
        audio.terminate()
        print("\n✅ 音声入力を終了しました")

    # 文字起こし結果を取得
    return handler.get_final_transcript()


def load_custom_instructions() -> str:
    """カスタムインストラクションファイルを読み込む"""
    try:
        with open(".custom-instructions", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""
    except Exception as e:
        print(f"カスタムインストラクション読み込みエラー: {e}")
        return ""


def build_system_prompt(base_prompt: str) -> str:
    """ベースプロンプトにカスタムインストラクションを組み合わせたシステムプロンプトを構築"""
    custom_instructions = load_custom_instructions()

    if custom_instructions:
        return f"""{base_prompt}

ただし、今回のこのタスクに関しては、追加の指示がありますので、以下に提示します。上記の指示と矛盾する場合は、以下の追加指示を優先してください。

{custom_instructions}"""
    else:
        return base_prompt


def summarize_meeting(transcript: str) -> str:
    """Bedrock を使用して朝会の要約を生成"""
    bedrock = boto3.client("bedrock-runtime", region_name="ap-northeast-1")

    base_system_prompt = f"""
あなたはチーム開発の朝会議事録を作成するアシスタントです。
現在時刻: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

以下の文字起こし結果から、Slack投稿用の簡潔な議事録を作成してください。

要件:
- 内容を箇条書きで記載し、各項目は完結した文章にする
- 箇条書きの間は空行を入れずに詰める
- タスク関連の内容は除外（別途Issue化するため）
- 決定事項、進捗報告、問題点、方針変更などを具体的に記載
- 見出しだけでなく、状況や結果も含めて記述する
- 日本語で出力

フォーマット例:
- メンバーAの進捗状況は順調で、APIの実装が80%完了しています。
- 新機能Xの設計方針について議論し、マイクロサービス化の方向で合意しました。
- チーム体制の変更により、来月からフロントエンド担当者が1名増員されます。
- パフォーマンス問題が発生しており、データベースクエリの最適化が必要です。

文字起こし結果:
{transcript}
"""

    system_prompt = build_system_prompt(base_system_prompt)

    try:
        import json

        response = bedrock.invoke_model(
            modelId="apac.anthropic.claude-sonnet-4-20250514-v1:0",
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": "議事録を作成してください。"}
                    ],
                }
            ),
        )

        response_body = json.loads(response["body"].read().decode("utf-8"))
        return response_body["content"][0]["text"]
    except Exception as e:
        print(f"要約生成エラー: {e}")
        return f"要約生成に失敗しました。元の文字起こし:\n{transcript}"


def extract_tasks(transcript: str) -> list[Task]:
    """Bedrock を使用してタスクを抽出"""
    bedrock = boto3.client("bedrock-runtime", region_name="ap-northeast-1")

    current_time = datetime.now()
    base_system_prompt = f"""
あなたはチーム開発の朝会からタスクを抽出するアシスタントです。
現在時刻: {current_time.strftime("%Y-%m-%d %H:%M:%S")}

以下の文字起こし結果から、Issue化すべきタスクを抽出してください。

抽出条件:
- まだ完了していないタスク
- 具体的な作業内容が含まれているもの
- 依頼事項や新規作業

各タスクについて以下の形式でJSONで出力してください:
[
  {{
    "title": "【{{deadline}}】{{task_title}}",
    "body": "## 背景\\n- {{background_info_if_available}}\\n\\n## 担当者\\n- {{assignees_if_mentioned}}\\n\\n## やること\\n- {{task_details}}",
    "deadline": "{{deadline_date}}",
    "assignees": ["{{github_username1}}", "{{github_username2}}"],
    "labels": ["{{label1}}", "{{label2}}"]
  }}
]

タイトルの締切形式:
- チーム内決定: "【とりあえず{{日付}}まで】"
- 外部依頼/必須: "【{{日付}}まで】"
- 相対日付は絶対日付に変換（今日=2025-06-XX、明日=2025-06-XX、来週金曜=2025-06-XX）

Issue本文の作成ルール:
- 背景: そのタスクの背景が読み取れた場合のみ記載、不明な場合は空欄
- 担当者: 担当者について話していた場合は名前のみ記載、不明な場合は空欄
- やること: そのタスクでやるとされていたことを具体的に記載

追加フィールドの設定:
- assignees: GitHubのユーザー名が特定できる場合は配列で記載（例: ["statiolake", "user2"]）、不明な場合は空配列
- labels: 特別な指示がない限り空配列を指定してください

文字起こし結果:
{transcript}
"""

    system_prompt = build_system_prompt(base_system_prompt)

    try:
        import json

        response = bedrock.invoke_model(
            modelId="apac.anthropic.claude-sonnet-4-20250514-v1:0",
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": "タスクをJSON形式で抽出してください。",
                        }
                    ],
                }
            ),
        )

        response_body = json.loads(response["body"].read().decode("utf-8"))
        result_text = response_body["content"][0]["text"]

        # JSON部分を抽出してパース
        import re

        json_match = re.search(r"\[.*\]", result_text, re.DOTALL)
        if json_match:
            raw_tasks = json.loads(json_match.group())
            return [
                Task(
                    title=task["title"],
                    body=task["body"],
                    deadline=task["deadline"],
                    assignees=task.get("assignees", []),
                    labels=task.get("labels", []),
                )
                for task in raw_tasks
            ]
        else:
            return []
    except Exception as e:
        print(f"タスク抽出エラー: {e}")
        return []


def edit_issues_in_editor(issues: list[Issue]) -> list[Issue]:
    """エディタでIssueの編集"""
    editor = os.environ.get("EDITOR", "nvim")

    # 一時ファイルに issue 情報を書き込み
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("; Issues to Create\n\n")
        f.write(
            "; 以下のIssueを編集してください。不要なIssueブロックは削除してください。\n"
        )
        f.write("; フォーマット: タイトル行の後に本文、Issueは --- で区切ります。\n\n")

        for i, issue in enumerate(issues):
            # AI生成内容から既存の --- を除去
            clean_title = issue.title.replace("---", "").strip()
            clean_body = issue.body.replace("---", "").strip()

            # assigneesとlabelsをタイトルに追加
            title_parts = [clean_title]

            if issue.assignees:
                assignee_mentions = " ".join(
                    [f"@{assignee}" for assignee in issue.assignees]
                )
                title_parts.append(assignee_mentions)

            if issue.labels:
                label_mentions = " ".join([f"<[{label}]>" for label in issue.labels])
                title_parts.append(label_mentions)

            f.write(f"# {' '.join(title_parts)}\n")
            f.write(f"{clean_body}\n")

            # 最後のIssue以外は区切り線を追加
            if i < len(issues) - 1:
                f.write("\n---\n\n")

        temp_path = f.name

    # エディタを開く
    subprocess.run([editor, temp_path])

    # 編集結果を読み込み
    with open(temp_path, "r") as f:
        content = f.read()

    os.unlink(temp_path)

    # 編集されたissueを解析
    edited_issues = []

    # ; で始まるコメント行を削除
    lines = content.split("\n")
    filtered_lines = [line for line in lines if not line.strip().startswith(";")]
    filtered_content = "\n".join(filtered_lines)

    # --- で分割してIssueブロックを取得
    issue_blocks = filtered_content.split("---")

    for block in issue_blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        title = ""
        body_lines = []
        assignees: list[str] = []
        labels: list[str] = []

        for line in lines:
            if line.strip().startswith("#") and not title:
                # 最初の # 見出しをタイトルとする
                raw_title = line.strip().lstrip("#").strip()

                # タイトルをパースして要素を抽出
                parsed_title = parse_issue_title(raw_title)
                title = parsed_title.title
                assignees = parsed_title.assignees
                labels = parsed_title.labels

            elif title:
                # タイトル後の内容を本文とする
                body_lines.append(line)

        if title:
            edited_issues.append(
                Issue(
                    title=title,
                    body="\n".join(body_lines).strip(),
                    assignees=assignees,
                    labels=labels,
                )
            )

    return edited_issues


def create_github_issues(
    issues: list[Issue], repo: str, project: str | None = None
) -> list[str]:
    """GitHub Issues を作成"""

    issue_urls = []
    for issue in issues:
        try:
            # 基本的なコマンド引数
            cmd = [
                "gh",
                "issue",
                "create",
                "--repo",
                repo,
                "--title",
                issue.title,
                "--body",
                issue.body,
            ]

            # assigneesが指定されている場合は追加
            if issue.assignees:
                for assignee in issue.assignees:
                    cmd.extend(["--assignee", assignee])

            # labelsが指定されている場合は追加
            if issue.labels:
                for label in issue.labels:
                    cmd.extend(["--label", label])

            # projectが指定されている場合は追加
            if project:
                cmd.extend(["--project", project])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                issue_url = result.stdout.strip()
                issue_urls.append(issue_url)
                assignee_info = (
                    f" (assigned to {', '.join([f'@{a}' for a in issue.assignees])})"
                    if issue.assignees
                    else ""
                )
                label_info = (
                    f" (labels: {', '.join(issue.labels)})" if issue.labels else ""
                )
                project_info = f" (added to project: {project})" if project else ""
                print(
                    f"Issue created: {issue_url}{assignee_info}{label_info}{project_info}"
                )
            else:
                print(f"Issue 作成失敗: {result.stderr}")
        except Exception as e:
            print(f"Issue 作成エラー: {e}")

    return issue_urls


def post_to_slack(webhook_url: str, summary: str, issue_urls: list[str]) -> bool:
    """Slack にBlock Kitを使って議事録とIssue一覧を投稿"""
    try:
        # 議事録セクション
        blocks: list[dict] = [  # type: ignore
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📝 朝会議事録", "emoji": True},
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": f"```{summary}```"}},
        ]

        # Issue一覧セクション
        if issue_urls:
            blocks.append({"type": "divider"})
            blocks.append(
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 作成されたIssue",
                        "emoji": True,
                    },
                }
            )

            # Issue URLsをリスト形式で表示
            issue_list = []
            for i, url in enumerate(issue_urls, 1):
                # URLからIssue番号を抽出
                issue_number = url.split("/")[-1] if "/" in url else str(i)
                issue_list.append(f"• <{url}|Issue #{issue_number}>")

            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "\n".join(issue_list)},
                }
            )

            # 統計情報
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📊 合計 {len(issue_urls)} 件のIssueを作成しました",
                        }
                    ],
                }
            )
        else:
            blocks.append({"type": "divider"})
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "ℹ️ 今回は新しいIssueは作成されませんでした",
                    },
                }
            )

        # フッター
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🤖 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} に自動生成",
                    }
                ],
            }
        )

        payload = {"blocks": blocks, "unfurl_links": False, "unfurl_media": False}

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

        print("✅ Slack に投稿しました")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Slack投稿エラー: {e}")
        return False
    except Exception as e:
        print(f"❌ Slack投稿で予期しないエラー: {e}")
        return False


def parse_args():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description="朝会の文字起こしからIssueを自動作成するツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # マイクロフォンから音声入力
  python main.py --repo owner/repository

  # stdinからテキスト入力
  echo "朝会の内容..." | python main.py --repo owner/repository
        """,
    )
    parser.add_argument(
        "--repo", required=True, help="GitHubリポジトリ (例: owner/repository)"
    )
    parser.add_argument("--project", help="すべてのIssueに設定するデフォルトproject名")
    parser.add_argument(
        "--slack-incoming-webhook",
        help="議事録とIssueをSlackに投稿するためのIncoming Webhook URL",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    print("=" * 60)
    print("📱 朝会議事録 & Issue作成ツール")
    print("=" * 60)
    print(f"📂 リポジトリ: {args.repo}")
    print("─" * 60)

    try:
        # 1. 入力取得（stdin または音声）
        transcript = await get_input_text()

        if not transcript.strip():
            print("❌ 入力が空です。")
            return

        # 2. 議事録生成
        print("📝 議事録を生成中...")
        summary = summarize_meeting(transcript)

        print("✅ 生成された議事録")
        print("─" * 60)
        print(summary)
        print()

        # 3. タスク抽出
        print("🔍 タスクを抽出中...")
        tasks = extract_tasks(transcript)

        issue_urls = []
        if not tasks:
            print("✅ 抽出されたタスクはありませんでした。")
            # Slackに議事録のみ投稿
            if args.slack_incoming_webhook:
                post_to_slack(args.slack_incoming_webhook, summary, [])
            return

        # TaskをIssueに変換
        issues = [
            Issue(
                title=task.title,
                body=task.body,
                assignees=task.assignees,
                labels=task.labels,
            )
            for task in tasks
        ]

        # 4. Issue編集
        print(f"✏️  {len(issues)}個のIssueを編集中...")
        edited_issues = edit_issues_in_editor(issues)

        if not edited_issues:
            print("✅ 編集後のIssueがありませんでした。")
            # Slackに議事録のみ投稿
            if args.slack_incoming_webhook:
                post_to_slack(args.slack_incoming_webhook, summary, [])
            return

        # 5. GitHub Issue作成
        print(f"🚀 {len(edited_issues)}個のIssueを作成中...")
        issue_urls = create_github_issues(edited_issues, args.repo, args.project)

        # 6. 結果表示
        print(f"✅ 作成されたIssue ({len(issue_urls)}件)")
        print("─" * 60)
        for i, url in enumerate(issue_urls, 1):
            print(f"  {i}. {url}")

        # 7. Slack投稿
        if args.slack_incoming_webhook:
            print("📤 Slack に投稿中...")
            post_to_slack(args.slack_incoming_webhook, summary, issue_urls)

    except KeyboardInterrupt:
        print("⚠️  処理を中断しました。")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")


def cli():
    """Entry point for console script"""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
