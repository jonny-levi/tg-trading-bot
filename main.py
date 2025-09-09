# main.py
from dotenv import load_dotenv
from config import FINNHUB_API_KEY, APP_URL
from keep_alive import keep_alive
from stock_fetcher import get_microcap_symbols
from websocket_handler import start_websocket
from metrics_service import start_metrics
from telegram_service import send_to_telegram
from youtube_watchlist import fetch_watchlist_from_youtube
import logger, logging, os

load_dotenv()

def run_bot():
    try:
        if not (os.getenv("FINNHUB_API_KEY") or FINNHUB_API_KEY):
            logging.error("❌ FINNHUB_API_KEY חסר. בדוק .env או config.py")
            send_to_telegram("❌ שגיאה: FINNHUB_API_KEY חסר.")
            return

        keep_alive()

        wl = fetch_watchlist_from_youtube()
        if wl:
            send_to_telegram(f"🧭 Watchlist מיוטיוב (ניסיון): {', '.join(wl[:12])}" + ("..." if len(wl) > 12 else ""))

        send_to_telegram("✅ הבוט הופעל. סורק מועמדים ומדליק חיבורי RT...")

        symbols_info = get_microcap_symbols(limit=50, priority_symbols=wl)
        if not symbols_info:
            send_to_telegram("⚠️ לא נמצאו מועמדים שעומדים בקריטריונים כרגע.")
            return

        # לוג קצר
        for s in symbols_info[:10]:
            logging.info("SELECTED %s | score=%s tier=%s | sf=%.1f rvol=%s",
                         s["symbol"], s.get("score"), s.get("tier"), s.get("short_float", 0.0), s.get("rvol"))

        # RT: WebSocket טיקים + Metrics פולינג לנרות 1ד׳
        start_websocket(symbols_info)
        start_metrics(symbols_info, poll_sec=30)

        send_to_telegram("🔔 התראות מופעלות: VWAP / VolumeSpike / HOD / Heads-up ל-Tier B + חדשות עם סנטימנט.")

    except Exception as e:
        logging.exception("❌ שגיאה בהפעלת הבוט:")
        try:
            send_to_telegram(f"❌ שגיאה בהפעלת הבוט:\n{e}")
        except Exception:
            pass

if __name__ == "__main__":
    run_bot()
