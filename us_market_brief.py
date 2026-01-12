import os
import requests
import datetime
import traceback

import yfinance as yf
from openai import OpenAI

# =========================
# 環境変数
# =========================
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# ユーティリティ
# =========================
def now_jst():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)

def safe_float(v):
    try:
        return float(v)
    except:
        return None

# =========================
# マーケットデータ取得
# =========================
def fetch_market(ticker):
    df = yf.download(ticker, period="2mo", interval="1d", progress=False)
    if len(df) < 2:
        return None

    cur = df.iloc[-1]
    prev = df.iloc[-2]

    return {
        "ticker": ticker,
        "close": safe_float(cur["Close"]),
        "change_pct": safe_float((cur["Close"] / prev["Close"] - 1) * 100),
        "high": safe_float(cur["High"]),
        "low": safe_float(cur["Low"]),
        "prev_high": safe_float(prev["High"]),
        "prev_low": safe_float(prev["Low"]),
        "volume": int(cur["Volume"]),
        "avg_volume_20": int(df["Volume"].tail(20).mean())
    }

# =========================
# テクニカル判定
# =========================
def tech_comment(d):
    if d["high"] > d["prev_high"] and d["volume"] > d["avg_volume_20"]:
        return "出来高を伴う上方ブレイク"
    if d["low"] < d["prev_low"] and d["volume"] > d["avg_volume_20"]:
        return "出来高を伴う下方ブレイク"
    return "明確なブレイクなし"

# =========================
# AI生成（フォールバック付き）
# =========================
def ai_generate(prompt, fallback):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "あなたは米国株と半導体市場を分析する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return fallback

# =========================
# 18:00 NVIDIA + 半導体シナリオ
# =========================
def evening_scenario(nvda, sox):
    prompt = f"""
以下は本日の米国株データです。

【NVDA】
終値: {nvda['close']}
前日比: {nvda['change_pct']:.2f}%
テクニカル: {tech_comment(nvda)}

【SOX】
前日比: {sox['change_pct']:.2f}%
テクニカル: {tech_comment(sox)}

18:00時点の想定として、
・NVDAと半導体全体を同じ比重で
・ニュース、需給、テクニカルを整理
・10分程度で読める分析文
を日本語で作成してください。
"""

    fallback = f"""
NVDAと半導体指数はいずれも明確なトレンドブレイクは見られず、
短期的には方向感待ちの局面。

NVDAは個別材料待ち、半導体全体も指数主導のレンジ推移が続いている。
18:00時点では無理なポジション構築より、出来高変化と
上限・下限の攻防を見極めるフェーズ。
"""

    return ai_generate(prompt, fallback)

# =========================
# メッセージ構築
# =========================
def build_message():
    nvda = fetch_market("NVDA")
    sox = fetch_market("^SOX")
    nas = fetch_market("^IXIC")

    now = now_jst().strftime("%Y-%m-%d %H:%M JST")

    scenario = evening_scenario(nvda, sox)

    return f"""
━━━━━━━━━━━━━━━━━━
【18:00 米国株・半導体レビュー】
━━━━━━━━━━━━━━━━━━

【指数動向】
NASDAQ: {nas['change_pct']:.2f}%

【NVDA】
終値: {nvda['close']}
前日比: {nvda['change_pct']:.2f}%
テクニカル: {tech_comment(nvda)}

【半導体（SOX）】
前日比: {sox['change_pct']:.2f}%
テクニカル: {tech_comment(sox)}

━━━━━━━━━━━━━━━━━━
【18:00 シナリオ（NVDA × 半導体）】
━━━━━━━━━━━━━━━━━━
{scenario}

━━━━━━━━━━━━━━━━━━
配信時刻：{now}
※ 自動生成 / 投資助言ではありません
"""

# =========================
# Discord送信
# =========================
def send_discord(msg):
    payload = {"content": msg}
    requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)

# =========================
# 実行
# =========================
if __name__ == "__main__":
    try:
        message = build_message()
        send_discord(message)
    except Exception:
        send_discord("❌ 市場レビュー生成中にエラーが発生しました。\n" + traceback.format_exc())
