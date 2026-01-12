import os
import requests
import datetime
import openai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

openai.api_key = OPENAI_API_KEY

JST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(JST)

mode = "morning" if now.hour < 12 else "evening"
time_label = "6:00 JST" if mode == "morning" else "18:00 JST"

# -------------------------
# AI生成
# -------------------------
def generate_ai_text(prompt):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional US stock market analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )
        return res.choices[0].message.content
    except Exception:
        return None

# -------------------------
# プロンプト
# -------------------------
prompt = f"""
You are generating a US stock market report.

Requirements:
- Focus equally on NVIDIA (NVDA) and the semiconductor sector.
- Include sections:
  1. News (importance-based)
  2. US politics / political statements
  3. NVDA individual analysis
  4. Semiconductor sector overview
  5. Technical analysis
  6. Scenario analysis
  7. (Morning only) Validation of previous scenario
- Avoid irrelevant news.
- Professional tone, ~10 minutes reading volume.
- If no items exist, explicitly state "no notable items".

Time: {time_label}
"""

ai_text = generate_ai_text(prompt)

# -------------------------
# フォールバック
# -------------------------
if not ai_text:
    ai_text = """
【ニュース】
重要な新規材料は限定的。市場はテクニカル主導。

【米国政治】
FRB関連で特筆すべき新発言なし。

【NVDA】
方向感待ちの調整局面。

【半導体】
SOXは指数と同程度の動き。

【シナリオ】
レンジ継続がメイン。
"""

# -------------------------
# メッセージ組み立て
# -------------------------
message = f"""
━━━━━━━━━━━━━━━━━━
【米国株 市場レビュー】{time_label}
（米国株 / 半導体・NVDA中心）
━━━━━━━━━━━━━━━━━━
{ai_text}
━━━━━━━━━━━━━━━━━━
配信時刻：{now.strftime('%Y-%m-%d %H:%M')} JST
※ 自動生成 / 投資助言ではありません
"""

# -------------------------
# Discord送信
# -------------------------
requests.post(
    DISCORD_WEBHOOK_URL,
    json={"content": message}
)
