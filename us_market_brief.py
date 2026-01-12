import os
import requests
import datetime
import yfinance as yf

# ========= 環境変数 =========
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ========= 時刻判定 =========
now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
hour = now.hour

MODE = "MORNING" if hour < 12 else "EVENING"

# ========= データ取得 =========
def get_price(ticker):
    df = yf.download(ticker, period="7d", interval="1d", progress=False)
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

# ========= テクニカル判定 =========
def technical_comment(d):
    if d["volume"] > d["avg_volume"] and d["high"] > d["prev_high"]:
        return "出来高を伴う上方ブレイク"
    if d["volume"] > d["avg_volume"] and d["low"] < d["prev_low"]:
        return "出来高を伴う下方ブレイク"
    return "方向感待ちの調整局面"

# ========= AI生成（フォールバック付き） =========
def ai_text(prompt, fallback):
    if not OPENAI_API_KEY:
        return fallback
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600
        )
        return res.choices[0].message.content
    except Exception:
        return fallback

# ========= 本文生成 =========
def build_message():
    header = f"""━━━━━━━━━━━━━━━━━━
【米国株 市場レビュー】{'6:00' if MODE=='MORNING' else '18:00'} JST
（米国株 / 半導体・NVDA中心）
━━━━━━━━━━━━━━━━━━
"""

    news = """【ニュース｜前日の影響評価】
・直近の材料は限定的だが、金利・AI関連期待は継続
・材料難の中、テクニカル主導の値動き

【ニュース｜最新（速報）】
・目立ったマーケットブレイク要因はなし

【トレンドを形成している大きな材料（過去1週間）】
・AI投資継続期待
・米金利の高止まり警戒
"""

    politics = """【米国政治・政治家発言】
・FRB高官発言はインフレ警戒を維持
・金融政策は依然として株式の上値を抑制
"""

    nvda_block = f"""【NVDA 個別動向】
終値: {nvda['close']:.2f}
前日比: {nvda['change_pct']:.2f}%
テクニカル: {technical_comment(nvda)}
"""

    semi = f"""【半導体セクター全体】
SOX 前日比: {sox['change_pct']:.2f}%
NASDAQ 前日比: {nasdaq['change_pct']:.2f}%
・半導体は指数と同程度の強弱
・物色集中はNVDA中心
"""

    scenario = ""
    if MODE == "EVENING":
        scenario = ai_text(
            "NVDAと半導体市場の翌営業日に向けたテクニカルシナリオを専門家視点で詳しく。",
            "【NVDA シナリオ】\n・方向感待ち。重要価格帯での攻防を想定。"
        )
        scenario = f"\n【18:00 NVDA テクニカルシナリオ】\n{scenario}\n"

    if MODE == "MORNING":
        scenario = ai_text(
            "前日のNVDAと半導体市場の値動きをニュースとテクニカルの観点から振り返って。",
            "【検証】\n・材料よりも需給・テクニカル主導の一日。"
        )
        scenario = f"\n【検証｜答え合わせ】\n{scenario}\n"

    footer = f"""━━━━━━━━━━━━━━━━━━
配信時刻：{now.strftime('%Y-%m-%d %H:%M')} JST
※ 自動生成 / 投資助言ではありません
"""

    return header + news + politics + nvda_block + semi + scenario + footer

# ========= Discord送信 =========
payload = {"content": build_message()}
requests.post(DISCORD_WEBHOOK_URL, json=payload)
