import os
import requests
import datetime
import openai

# =====================
# 環境変数
# =====================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
openai.api_key = OPENAI_API_KEY

# =====================
# 時刻判定
# =====================
JST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(JST)

MODE = "MORNING" if now.hour < 12 else "EVENING"
TIME_LABEL = "6:00 JST" if MODE == "MORNING" else "18:00 JST"

# =====================
# 固定データ（将来API化前提）
# =====================
NVDA_DATA = {
    "close": 184.86,
    "change_pct": -0.10,
    "volume_comment": "出来高は平均的"
}

SEMI_DATA = {
    "SOX": {"close": 7638.78, "change_pct": 2.73},
    "NASDAQ": {"change_pct": 0.81}
}

# =====================
# ニュース（重要度別・手動でも崩れない構造）
# =====================
NEWS_IMPORTANT = [
    "NVIDIA関連AI投資は継続姿勢を維持",
    "半導体設備投資の減速懸念は限定的"
]

NEWS_SUPPLEMENT = [
    "個別企業ニュースは散発的",
    "材料は概ね織り込み済み"
]

POLITICAL = [
    "FRB高官はインフレ警戒姿勢を維持",
    "金融政策は株式の上値を抑制"
]

# =====================
# プロンプト（構造を強制）
# =====================
def build_prompt():
    return f"""
以下の構造を【必ず】守って文章を生成してください。
推測・創作は禁止。

【ニュース｜重要】
{chr(10).join('・'+n for n in NEWS_IMPORTANT)}

【ニュース｜補足】
{chr(10).join('・'+n for n in NEWS_SUPPLEMENT)}

【米国政治・政治家発言】
{chr(10).join('・'+p for p in POLITICAL)}

【NVDA 個別動向】
終値 {NVDA_DATA['close']} / 前日比 {NVDA_DATA['change_pct']}%
{NVDA_DATA['volume_comment']}

【半導体セクター】
SOX 前日比 {SEMI_DATA['SOX']['change_pct']}%
NASDAQ 前日比 {SEMI_DATA['NASDAQ']['change_pct']}%
NVDAとの相対評価を必ず記述。

【テクニカル】
ブレイク有無・レンジ・出来高の意味。

【{TIME_LABEL} シナリオ】
上・横・下の3パターン。

{"【前回シナリオの検証】も必須。" if MODE == "MORNING" else ""}
文章量は10分想定。
"""

# =====================
# AI生成
# =====================
def ai_generate(prompt):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional US equity market analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return res.choices[0].message.content
    except Exception:
        return None

ai_text = ai_generate(build_prompt())

# =====================
# フォールバック（構造保持）
# =====================
if not ai_text:
    ai_text = f"""
【ニュース｜重要】
・AI投資期待は継続

【ニュース｜補足】
・材料は概ね出尽くし

【米国政治・政治家発言】
・FRBは引き締め姿勢を維持

【NVDA 個別動向】
方向感待ちの調整局面。

【半導体セクター】
指数と同程度の推移。

【テクニカル】
レンジ内推移、出来高は落ち着き。

【{TIME_LABEL} シナリオ】
・上：出来高伴えば続伸
・横：レンジ継続
・下：利益確定売り
"""

# =====================
# Discord送信
# =====================
message = f"""
━━━━━━━━━━━━━━━━━━
【米国株 市場レビュー】{TIME_LABEL}
（米国株 / 半導体・NVDA中心）
━━━━━━━━━━━━━━━━━━
{ai_text}
━━━━━━━━━━━━━━━━━━
配信時刻：{now.strftime('%Y-%m-%d %H:%M')} JST
※ 自動生成 / 投資助言ではありません
"""

requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
