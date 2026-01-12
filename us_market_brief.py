import os
import requests
from datetime import datetime, timedelta
import pytz

# =====================
# ENV
# =====================
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

JST = pytz.timezone("Asia/Tokyo")
now = datetime.now(JST)
hour = now.hour
MODE = "EVENING" if hour >= 17 else "MORNING"

# =====================
# OpenAI
# =====================
def ai(text):
    if not OPENAI_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは米国株と半導体専門の市場アナリストです。"},
                {"role": "user", "content": text}
            ],
            temperature=0.35
        )
        return res.choices[0].message.content
    except:
        return None

# =====================
# News
# =====================
def get_news():
    if not NEWS_API_KEY:
        return "・重要ニュースなし（API未設定）"
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "q": "NVIDIA OR semiconductor OR Federal Reserve",
        "language": "en",
        "apiKey": NEWS_API_KEY,
        "pageSize": 5
    }
    r = requests.get(url, params=params).json()
    lines = []
    for a in r.get("articles", []):
        lines.append(f"・{a['title']}")
    return "\n".join(lines) if lines else "・目立ったニュースなし"

# =====================
# Market Data（簡易）
# =====================
def market_snapshot():
    # 実運用では yfinance 等に差し替え可能
    return {
        "NVDA": "方向感なし（レンジ）",
        "SOX": "高値圏維持",
        "NASDAQ": "押し目買い優勢"
    }

# =====================
# Main Message
# =====================
def build_text():
    news = get_news()
    market = market_snapshot()

    if MODE == "EVENING":
        prompt = f"""
以下を満たす18:00用シナリオを作成：

・NVDAと半導体を同比重
・テクニカル中心（出来高、ブレイク）
・2シナリオ（上/下）
・ニュースと政治要因も反映

ニュース：
{news}

市場状況：
{market}
"""
    else:
        prompt = f"""
以下を満たす6:00用レビューを作成：

・前日の値動き検証
・NVDA / 半導体の答え合わせ
・ニュースが効いたか
・政治・発言の影響
・10分想定

ニュース：
{news}

市場状況：
{market}
"""

    return ai(prompt) or "AI生成失敗（フォールバック）"

# =====================
# Discord Embed
# =====================
def send():
    content = build_text()
    embed = {
        "title": "🇺🇸 米国株 / 半導体マーケット",
        "description": content[:3900],
        "footer": {
            "text": f"{now.strftime('%Y-%m-%d %H:%M JST')}｜自動生成・投資助言ではありません"
        }
    }
    requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})

send()
