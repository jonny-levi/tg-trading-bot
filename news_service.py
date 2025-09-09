# news_service.py
import logging
import requests
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import FINNHUB_API_KEY

_session = requests.Session()
_analyzer = SentimentIntensityAnalyzer()

def _sent_emoji(texts: list[str]) -> str:
    if not texts: return "⚪"
    scores = [_analyzer.polarity_scores(t).get("compound", 0.0) for t in texts]
    avg = sum(scores) / len(scores)
    if avg >= 0.25: return "🟢"
    if avg <= -0.25: return "🔴"
    return "⚪"

def get_today_news(symbol: str) -> str:
    try:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        url = (
            "https://finnhub.io/api/v1/company-news"
            f"?symbol={symbol}&from={today}&to={today}&token={FINNHUB_API_KEY}"
        )
        r = _session.get(url, timeout=6)
        r.raise_for_status()
        res = r.json()
        if not res:
            return "📰 חדשות היום: אין חדשות עדכניות."
        headlines = []
        for item in res[:3]:
            h = str(item.get("headline", "")).strip()
            if len(h) > 140: h = h[:137] + "..."
            headlines.append(h)
        senti = _sent_emoji(headlines)
        return "📰 חדשות היום " + senti + ":\n" + "\n".join([f"• 🔹 {h}" for h in headlines])
    except Exception as e:
        logging.error("News fetch error for %s: %s", symbol, e)
        return "📰 חדשות היום: שגיאה בשליפה."
