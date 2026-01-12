import os
import datetime
import requests
import yfinance as yf
import feedparser

# =====================
# 環境変数
# =====================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# =====================
# 時刻・モード判定
# =====================
now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
hour = now.hour
MODE = "MORNING" if hour < 12 else "EVENING"

# =====================
# 株価データ取得
# =====================
def get_price(ticker):
    df = yf.download(ticker, period="10d", interval="1d", progress=False)
    cur = df.iloc[-1]
    prev = df.iloc[-2]

    return {
        "close": float(cur["Close"]),
        "change_pct": float((cur["Close"] / prev["Close"] - 1) * 100),
        "high": float(cur["High"]),
        "low": float(cur["Low"]),
        "prev_high": float(prev["High"]),
        "prev_low": float(prev["Low"]),
        "volume": int(cur["Volume"]),
        "avg_volume": int(df["Volume"].tail(5).mean())
    }

nvda = get_price("NVDA")
sox = get_price("^SOX")
nasdaq = get_price("^IXIC")

# =====================
# テクニカル分析（説明付き）
# =====================
def technical_analysis(name, d):
    text = f"{name}は終値{d['close']:.2f}（前日比 {d['change_pct']:.2f}%）。"
    if d["volume"] > d["avg_volume"] and d["high"] > d["prev_high"]:
        text += "出来高を伴って前日高値を上抜けており、短期的にはブレイク局面。"
    elif d["volume"] > d["avg_volume"] and d["low"] < d["prev_low"]:
        text += "出来高を伴う下押しで、調整圧力が強まった形。"
    else:
        text += "出来高は平均的で、重要価格帯での様子見・調整局面。"
    return text

# =====================
# ニュース取得（RSS）
# =====================
def fetch_news():
    urls = [
        "https://finance.yahoo.com/rss/headline?s=NVDA",
        "https://finance.yahoo.com/rss/industry?s=semiconductors",
        "https://finance.yahoo.com/rss/politics"
    ]
    headlines = []
    for url in urls:
        feed = feedparser.parse(url)
        for e in feed.entries[:3]:
            headlines.append(e.title)
    return headlines

news_list = fetch_news()

# =====================
# AI生成（失敗時フォールバック）
# =====================
def ai_generate(prompt, fallback):
    if not OPENAI_API_KEY:
        return fallback
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700
        )
        return res.choices[0].message.content
    except Exception:
        return fallback

# =====================
# 本文生成
# =====================
def build_message():
    header = f"""━━━━━━━━━━━━━━━━━━
【米国株 市場レビュー】{'6:00' if MODE=='MORNING' else '18:00'} JST
（米国株 / 半導体・NVDA中心）
━━━━━━━━━━━━━━━━━━
"""

    news_block = "【ニュース｜最新・影響評価】\n"
    for n in news_list:
        news_block += f"・{n}\n"

    ai_news = ai_generate(
        f"以下のニュースが米国株、特に半導体とNVDAに与える影響を分析してください:\n{news_list}",
        "・ニュースはあるが、市場は織り込み済みで反応は限定的。"
    )

    tech_block = f"""
【NVDA テクニカル】
{technical_analysis("NVDA", nvda)}

【半導体セクター】
{technical_analysis("SOX指数", sox)}
NASDAQとの比較では半導体は{'アウトパフォーム' if sox['change_pct'] > nasdaq['change_pct'] else '指数並み〜アンダーパフォーム'}。
"""

    scenario = ""
    if MODE == "EVENING":
        scenario = ai_generate(
            "NVDAと半導体指数の翌営業日に向けたテクニカルシナリオを3パターンで。",
            "・上：出来高増で続伸\n・横：レンジ継続\n・下：利益確定売り"
        )
        scenario = f"\n【18:00 NVDA シナリオ】\n{scenario}\n"

    if MODE == "MORNING":
        scenario = ai_generate(
            "前日のNVDAと半導体の値動きをニュースとテクニカルから検証してください。",
            "・材料よりも需給主導の一日。"
        )
        scenario = f"\n【検証｜前日答え合わせ】\n{scenario}\n"

    footer = f"""━━━━━━━━━━━━━━━━━━
配信時刻：{now.strftime('%Y-%m-%d %H:%M')} JST
※ 自動生成 / 投資助言ではありません
"""

    return header + news_block + ai_news + tech_block + scenario + footer

# =====================
# Discord送信
# =====================
requests.post(DISCORD_WEBHOOK_URL, json={"content": build_message()})
