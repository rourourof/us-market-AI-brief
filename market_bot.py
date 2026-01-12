import os
import requests
import datetime
import pandas as pd
import numpy as np
import openai

# =====================
# 環境変数
# =====================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # newsapi.org 等

openai.api_key = OPENAI_API_KEY

# =====================
# 時刻管理
# =====================
JST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(JST)
MODE = "MORNING" if now.hour < 12 else "EVENING"
TIME_LABEL = "6:00 JST" if MODE == "MORNING" else "18:00 JST"

# =====================
# ニュース取得
# =====================
def fetch_news():
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "NVIDIA OR semiconductor OR Fed OR interest rate",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
        "apiKey": NEWS_API_KEY
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    return data.get("articles", [])

# =====================
# ニュース重要度分類
# =====================
def score_news(article):
    title = article["title"].lower()
    score = 0

    if "nvidia" in title:
        score += 3
    if "semiconductor" in title or "chip" in title:
        score += 2
    if "fed" in title or "interest rate" in title:
        score += 2
    if "guidance" in title or "earnings" in title:
        score += 2

    if score >= 4:
        return "重要"
    elif score >= 2:
        return "中"
    else:
        return "参考"

def classify_news(articles):
    important, medium, low = [], [], []
    for a in articles:
        level = score_news(a)
        text = a["title"]
        if level == "重要":
            important.append(text)
        elif level == "中":
            medium.append(text)
        else:
            low.append(text)
    return important, medium, low

# =====================
# テクニカル（ダミーデータ前提）
# ※ 将来API差し替え前提
# =====================
def technical_nvda():
    close = 184.86
    sma20 = 182.4
    sma50 = 176.8
    volume_ratio = 1.0

    if close > sma20 > sma50:
        trend = "上昇基調"
    elif close < sma20 < sma50:
        trend = "下落基調"
    else:
        trend = "レンジ"

    return {
        "close": close,
        "trend": trend,
        "volume_ratio": volume_ratio
    }

def technical_semiconductor():
    sox = 2.73
    nasdaq = 0.81

    if sox > nasdaq:
        strength = "アウトパフォーム"
    elif sox < nasdaq:
        strength = "アンダーパフォーム"
    else:
        strength = "指数並み"

    return {
        "sox": sox,
        "nasdaq": nasdaq,
        "strength": strength
    }

# =====================
# プロンプト構築
# =====================
def build_prompt(news_i, news_m, news_l, nvda, semi):
    return f"""
以下の構造を【厳守】して10分想定の市場レビューを書いてください。

━━━━━━━━━━━━━━━━━━
【ニュース｜重要】
{chr(10).join('・'+n for n in news_i[:5]) or '・重要材料なし'}

【ニュース｜中】
{chr(10).join('・'+n for n in news_m[:5]) or '・目立った材料なし'}

【ニュース｜参考】
{chr(10).join('・'+n for n in news_l[:5]) or '・補足的ニュース'}

【米国政治・金融政策】
FRB・金利の影響を必ず記述。

【NVDA 個別動向】
終値 {nvda['close']}
テクニカル評価：{nvda['trend']}
出来高評価も含める。

【半導体セクター】
SOX 前日比 {semi['sox']}%
NASDAQ 前日比 {semi['nasdaq']}%
相対評価：{semi['strength']}

【テクニカル総括】
ブレイク有無・レンジ判定。

【{TIME_LABEL} シナリオ】
上・横・下の3シナリオ。

{"【前回シナリオの検証】を必ず含める。" if MODE == "MORNING" else ""}
━━━━━━━━━━━━━━━━━━
"""

# =====================
# AI生成
# =====================
def ai_generate(prompt):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional US equity market strategist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.35
        )
        return res.choices[0].message.content
    except Exception:
        return None

# =====================
# 実行
# =====================
articles = fetch_news()
news_i, news_m, news_l = classify_news(articles)

nvda = technical_nvda()
semi = technical_semiconductor()

prompt = build_prompt(news_i, news_m, news_l, nvda, semi)
text = ai_generate(prompt)

# フォールバック
if not text:
    text = f"""
【ニュース】
材料は出ているが市場反応は限定的。

【米国政治】
FRBは引き締め姿勢維持。

【NVDA】
{nvda['trend']}、方向感待ち。

【半導体】
{semi['strength']}。

【{TIME_LABEL} シナリオ】
・上：出来高伴えば続伸
・横：レンジ
・下：利益確定
"""

# =====================
# Discord送信
# =====================
final_message = f"""
━━━━━━━━━━━━━━━━━━
【米国株 市場レビュー】{TIME_LABEL}
（米国株 / 半導体・NVDA中心）
━━━━━━━━━━━━━━━━━━
{text}
━━━━━━━━━━━━━━━━━━
配信時刻：{now.strftime('%Y-%m-%d %H:%M')} JST
※ 自動生成 / 投資助言ではありません
"""

requests.post(DISCORD_WEBHOOK_URL, json={"content": final_message})
