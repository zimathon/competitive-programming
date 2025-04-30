import os
import requests
import json
import random
import sys

# 定数
PROBLEMS_API_URL = "https://kenkoooo.com/atcoder/resources/problems.json"
ATCODER_CONTEST_URL_FORMAT = "https://atcoder.jp/contests/{contest_id}"
ATCODER_TASK_URL_FORMAT = "https://atcoder.jp/contests/{contest_id}/tasks/{problem_id}"

# --- 設定 ---
# どのレベルの問題を対象とするか (例: 'B', 'C')
TARGET_PROBLEM_LEVELS = ['C', 'D']
# どのコンテスト種別を対象とするか (例: 'abc' for AtCoder Beginner Contest)
TARGET_CONTEST_PREFIX = 'abc'
# ----------------

def get_problems():
    """AtCoder Problems APIから問題リストを取得する"""
    print(f"Fetching problems from {PROBLEMS_API_URL}...")
    try:
        response = requests.get(PROBLEMS_API_URL)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生させる
        problems = response.json()
        print(f"Successfully fetched {len(problems)} problems.")
        return problems
    except requests.exceptions.RequestException as e:
        print(f"Error fetching problems: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}", file=sys.stderr)
        return None

def filter_problems(problems):
    """指定された条件 (コンテスト種別、問題レベル) で問題をフィルタリングする"""
    if not problems:
        return []

    filtered = []
    print(f"Filtering problems for contest prefix '{TARGET_CONTEST_PREFIX}' and levels {TARGET_PROBLEM_LEVELS}...")
    for problem in problems:
        # problem['id'] は 'abc123_a' のような形式
        # problem['contest_id'] は 'abc123' のような形式
        # problem['problem_index'] は 'A', 'B' などの大文字
        contest_id = problem.get('contest_id')
        problem_index = problem.get('problem_index')

        if contest_id and problem_index:
            # コンテストIDが指定プレフィックスで始まり、問題レベルがターゲットに含まれるか
            if contest_id.startswith(TARGET_CONTEST_PREFIX) and \
               problem_index in TARGET_PROBLEM_LEVELS:
                filtered.append(problem)

    print(f"Found {len(filtered)} matching problems.")
    return filtered

def select_problem(problems):
    """フィルタリングされた問題リストからランダムに1つ選ぶ"""
    if not problems:
        print("No problems available to select.", file=sys.stderr)
        return None
    return random.choice(problems)

def format_slack_message(problem):
    """Slackに送信するメッセージをBlock Kit形式で作成する"""
    if not problem:
        return {
            "text": "今日のおすすめ問題は見つかりませんでした。",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":warning: 今日のおすすめ問題は見つかりませんでした。"
                    }
                }
            ]
        }

    problem_id = problem.get('id', 'N/A')
    contest_id = problem.get('contest_id', 'N/A')
    problem_title = problem.get('title', 'N/A') # title は 'A - xxx' の形式
    problem_url = ATCODER_TASK_URL_FORMAT.format(contest_id=contest_id, problem_id=problem_id)
    contest_url = ATCODER_CONTEST_URL_FORMAT.format(contest_id=contest_id)

    # Slack Block Kit メッセージ
    message = {
        "text": f"今日の問題: {problem_title} ({contest_id})", # 通知用のテキスト
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":computer: *今日の競技プログラミング問題* ({TARGET_CONTEST_PREFIX.upper()} {', '.join(TARGET_PROBLEM_LEVELS)})"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*問題:* <{problem_url}|{problem_title}>\n*コンテスト:* <{contest_url}|{contest_id}>"
                }
            }
            # 必要であれば、ここに難易度情報などを追加 (problem-models.jsonが必要)
        ]
    }
    return message

def send_slack_notification(webhook_url, message):
    """Slack Incoming Webhookを使って通知を送信する"""
    if not webhook_url:
        print("Error: SLACK_WEBHOOK_URL environment variable not set.", file=sys.stderr)
        return False

    print("Sending notification to Slack...")
    try:
        response = requests.post(webhook_url, json=message, headers={'Content-Type': 'application/json'})
        response.raise_for_status() # HTTPエラーチェック
        if response.text == 'ok':
            print("Successfully sent notification to Slack.")
            return True
        else:
            print(f"Slack API returned an unexpected response: {response.text}", file=sys.stderr)
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending notification to Slack: {e}", file=sys.stderr)
        return False

def main():
    """メイン処理"""
    # 環境変数からWebhook URLを取得
    slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if not slack_webhook_url:
        print("Error: SLACK_WEBHOOK_URL is not set. Please set it in GitHub Secrets.", file=sys.stderr)
        sys.exit(1) # エラーで終了

    # 問題を取得・フィルタリング・選択
    all_problems = get_problems()
    filtered_problems = filter_problems(all_problems)
    selected_problem = select_problem(filtered_problems)

    # Slackメッセージを作成
    slack_message = format_slack_message(selected_problem)

    # Slackに通知
    success = send_slack_notification(slack_webhook_url, slack_message)

    if not success:
        sys.exit(1) # エラーで終了

if __name__ == "__main__":
    main()
