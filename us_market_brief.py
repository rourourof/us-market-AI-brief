import requests
import os
from datetime import datetime

WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")

if not WEBHOOK:
    raise RuntimeError("DISCORD_WEBHOOK_URL not set")

now = datetime.now().strftime("%Y-%m-%d %H:%M JST")

message = f"""━━━━━━━━━━━━━━━━━━
【テスト通知】
━━━━━━━━━━━━━━━━━━
GitHub Actionsからのテスト送信です。
時刻：{now}
━━━━━━━━━━━━━━━━━━
"""

requests.post(WEBHOOK, json={"content": message})
