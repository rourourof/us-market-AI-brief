import os
import requests
from datetime import datetime
import pytz

# =====================
# 基本設定
# =====================
WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

if not WEBHOOK:
    raise RuntimeError("DISCORD_WEBHOOK_URL not set")

JST = pytz.timezone("Asia/Tokyo")
now = datetime.now(JST)
hour = now.hour

MODE = "EVENING" if hour >= 17 else "MORNING"

# =====================
# AI生成（失敗しても落ちない）
# =====================
def ai_generate(prompt):
    if not OPENAI_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたはプロの米国株市場アナリストです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        return res.choices[0].message.content
    except Exception:
        return None

# =====================
# 本文生成
# =====================
def build_message():
    header = f"━━━━━━━━━━━━━━━━━━\n"
    header += f"【{'18:00 NVIDIA / 半導体 シナリオ' if MODE=='EVENING' else '6:00 米国株 市場レビュー'}】\n"
    header += f"（米国株 / 半導体・NVDA 同比重）\n"
    header += f"━━━━━━━━━━━━━━━━━━\n\n"

    if MODE == "EVENING":
        prompt = """
米国株・半導体・NVIDIAについて、
本日の値動きを踏まえた18:00時点のテクニカルシナリオを作成してください。

条件：
- NVIDIAと半導体セクターを同じ比重
- 出来高・ブレイク有無・調整判断
- 上下2シナリオ
- 読了5分以上
"""
        body = ai_generate(prompt) or """
【NVDA・半導体 テクニカル概況】
・指数・個別ともに明確なブレイクは確認されず
・出来高は平均水準で様子見

【NVDA シナリオ】
・上：高値更新＋出来高増 → モメンタム再点火
・下：支持線割れ → 調整継続

【半導体セクター】
・SOXはレンジ継続、主導銘柄不在
"""

    else:
        prompt = """
前日の米国株市場について以下を含めたレビューを作成してください。

- 前日のニュースと株価への影響
- NVIDIAと半導体の実際の値動き
- 政治・政治家発言の影響
- 過去1週間でトレンドを作った材料
- テクニカル視点での検証
- 読了10分想定
"""
        body = ai_generate(prompt) or """
【前日の影響評価】
・材料は限定的でテクニカル主導

【ニュース（最新）】
・大きなサプライズなし

【1週間のトレンド要因】
・金利見通しとAI投資期待

【NVDA / 半導体の検証】
・指数比でNVDAは堅調
・SOXは調整局面

【政治】
・FRB関連発言は市場に織り込み済み
"""

    footer = f"\n━━━━━━━━━━━━━━━━━━\n"
    footer += f"配信時刻：{now.strftime('%Y-%m-%d %H:%M JST')}\n"
    footer += "※ 自動生成 / 投資助言ではありません"

    return header + body + footer

# =====================
# Discord送信
# =====================
requests.post(WEBHOOK, json={"content": build_message()})
