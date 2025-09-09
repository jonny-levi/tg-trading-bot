# websocket_handler.py
# -*- coding: utf-8 -*-
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from collections import deque
from websocket import WebSocketApp

from telegram_service import send_to_telegram
from recommendation import generate_recommendation
from news_service import get_today_news
from config import FINNHUB_API_KEY
from session_time import get_session_label

# ===== פרמטרים =====
HISTORY_WINDOW = timedelta(minutes=30)  # כמה זמן לשמור היסטוריית מחירים לניטור MA(30m)
ALERT_EXPIRY   = timedelta(hours=1)     # ניקוי מפתחות התראה ישנים
ALERT_COOLDOWN = timedelta(minutes=5)   # קירור התראות לכל "באקט" אחוזים
PING_INTERVAL  = 20                     # שניות (ping לשמירת החיבור חי)
MAX_BACKOFF    = 120                    # שניות (גבול עליון לריב"ק התחברות)

# טריגרים ל-Tier B (מועמדות במעקב)
RVOL_TRIGGER_B      = 2.0              # RVOL דרוש כדי לשלוח Heads-up
CHANGE_TRIGGER_B_HP = 4.0              # שינוי יומי מ-Open ל-Heads-up מסוג "חזק"
CHANGE_TRIGGER_B_HI = 3.0              # שינוי יומי בעת HOD מקומי + מחיר מעל MA

# ===== זיכרון ריצה =====
price_history: dict[str, deque] = {}    # {symbol: deque[(ts, price)]}
sent_alerts: dict[str, datetime] = {}   # {key: last_sent_time}
_last_price: dict[str, float] = {}      # {symbol: last_trade_price} – להפחתת רעש כפולים
_local_hod: dict[str, float] = {}       # {symbol: local high-of-day מאז התחברות}

# ===== עזרים =====
def _cleanup_old_alerts(now: datetime):
    expired = [k for k, t in sent_alerts.items() if now - t > ALERT_EXPIRY]
    for k in expired:
        sent_alerts.pop(k, None)

def _should_alert(key: str, now: datetime) -> bool:
    """קירור התראות לפי מפתח ייחודי (למשל לפי סימול + באקט % שינוי + סוג-התראה)."""
    last = sent_alerts.get(key)
    if last and now - last < ALERT_COOLDOWN:
        return False
    sent_alerts[key] = now
    return True

def _fmt_money(x):
    try:
        x = float(x)
        if x >= 1_000_000_000: return f"${x/1_000_000_000:.2f}B"
        if x >= 1_000_000:     return f"${x/1_000_000:.2f}M"
        if x >= 1_000:         return f"${x/1_000:.2f}K"
        return f"${x:.0f}"
    except Exception:
        return "—"

def _adv_line(info: dict) -> str:
    """בונה שורת-מידע עשירה – Score, Short Float, RVOL, Avg$Vol, MCap, Gap% (אם קיימים)."""
    parts = []
    if (sc := info.get("score")) is not None:            parts.append(f"🧮 Score: <b>{int(sc)}/100</b>")
    if (sf := info.get("short_float")) is not None:      parts.append(f"🧷 Short Float: {sf:.1f}%")
    if (rv := info.get("rvol")) is not None:             parts.append(f"📦 RVOL: {rv:.2f}x")
    if (adv := info.get("avg_dollar_vol_10d")) is not None: parts.append(f"💵 Avg$Vol(10d): {_fmt_money(adv)}")
    if (mc := info.get("market_cap")) is not None:       parts.append(f"🏢 MCap: {_fmt_money(mc)}")
    if (gp := info.get("gap_pct")) is not None:          parts.append(f"🪜 Gap: {gp:.2f}%")
    return " | ".join(parts)

def _build_msg(symbol: str,
               price: float,
               open_price: float,
               avg_price: float,
               percent_change: float,
               info: dict,
               note: str,
               tag: str | None) -> str:
    arrow = "▲" if percent_change >= 0 else "▼"
    sign  = "+" if percent_change >= 0 else ""
    change_line = f"{arrow} <b>{sign}{percent_change:.2f}%</b>"

    # SSR (אם המחיר ≤ 90% מ־Prev Close) + חיווי Session
    ssr = ""
    pc = info.get("prev_close")
    try:
        if pc and float(price) <= 0.9 * float(pc):
            ssr = " • 🛡️ SSR ON"
    except Exception:
        pass
    session = get_session_label().upper()

    tech_line = f"💰 <b>${price:.2f}</b>  |  Open: ${open_price:.2f}  |  MA(30m): ${avg_price:.2f}  •  {session}{ssr}"
    adv_line  = _adv_line(info)

    header = "<b>📡 התראת מניה</b>" if not tag else f"<b>📡 {tag}</b>"
    footer = f"🔗 <a href='https://www.tradingview.com/symbols/{symbol}/'>גרף חי</a>  •  ⏱️ {datetime.now().strftime('%H:%M:%S')}"

    # חדשות
    try:
        news_block = get_today_news(symbol)
    except Exception as e:
        logging.error("news fetch error for %s: %s", symbol, e)
        news_block = "📰 חדשות היום: —"

    return (
        f"{header}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📈 <b>{symbol}</b>\n"
        f"{change_line}\n"
        f"{tech_line}\n"
        + (f"\n📝 {note}\n" if note else "") +
        (f"\n{adv_line}\n" if adv_line else "\n") +
        f"\n{news_block}\n"
        f"{footer}"
    )

def _send_full_alert(symbol, price, open_price, avg_price, percent_change, info):
    try:
        recommendation = generate_recommendation(round(percent_change, 2), price, avg_price)
    except Exception as e:
        logging.error("recommendation error for %s: %s", symbol, e)
        recommendation = "—"
    msg = _build_msg(symbol, price, open_price, avg_price, percent_change, info, note=f"🧠 {recommendation}", tag=None)
    send_to_telegram(msg)

def _send_heads_up(symbol, price, open_price, avg_price, percent_change, info, reason: str):
    msg = _build_msg(symbol, price, open_price, avg_price, percent_change, info, note=f"⚠️ Heads-up: {reason}", tag="Heads-up")
    send_to_telegram(msg)

# ===== לוגיקת עיבוד טיקים =====
def on_message(ws, message, symbols_info: list[dict]):
    """מטפל בהודעות נכנסות מה-WebSocket של Finnhub."""
    try:
        payload = json.loads(message)
        if "data" not in payload:
            return

        now = datetime.now()
        _cleanup_old_alerts(now)

        for item in payload["data"]:
            symbol = item.get("s")
            price  = item.get("p")
            if not symbol or price is None:
                continue

            # מציאת מידע על הסימול מהרשימה שנבנתה ע"י הסורק
            info = next((s for s in symbols_info if s.get("symbol") == symbol), None)
            if not info:
                continue

            open_price = info.get("open")
            if not open_price or open_price <= 0:
                continue

            # עדכון HOD מקומי
            prev_hod = _local_hod.get(symbol, float(price))
            if price > prev_hod:
                _local_hod[symbol] = float(price)

            # סינון טיקים זהים/רועשים
            last_p = _last_price.get(symbol)
            if last_p is not None and abs(price - last_p) < 1e-6:
                continue
            _last_price[symbol] = float(price)

            # היסטוריית מחיר ל-MA(30m)
            dq = price_history.setdefault(symbol, deque())
            dq.append((now, float(price)))
            while dq and now - dq[0][0] > HISTORY_WINDOW:
                dq.popleft()
            if not dq:
                continue

            prices = [p for _, p in dq]
            avg_price = sum(prices) / len(prices)
            percent_change = ((float(price) - float(open_price)) / float(open_price)) * 100.0

            # מפתחות קירור לפי "באקט" אחוזים
            pct_bucket = int(percent_change)
            full_key  = f"FULL_{symbol}_{pct_bucket}"
            head_key  = f"HEAD_{symbol}_{pct_bucket}"

            # ===== Tier A – התראה מלאה מיד =====
            if info.get("tier") == "A":
                if _should_alert(full_key, now):
                    _send_full_alert(symbol, price, open_price, avg_price, percent_change, info)
                continue  # ל-A אין צורך ב-Heads-up באותו באקט

            # ===== Tier B – Heads-up טריגרי =====
            rvol = info.get("rvol") or 0.0

            # 1) RVOL גבוה ושינוי חזק
            if rvol >= RVOL_TRIGGER_B and percent_change >= CHANGE_TRIGGER_B_HP:
                if _should_alert(head_key + "_RVOL", now):
                    _send_heads_up(symbol, price, open_price, avg_price, percent_change, info, reason="RVOL↑ ו-%Change↑")

            # 2) HOD מקומי חדש + שינוי ≥ 3% + מחיר מעל MA
            local_hod = _local_hod.get(symbol, float(price))
            made_new_hod = abs(float(price) - float(local_hod)) < 1e-6  # זה עתה נקבע HOD
            if made_new_hod and percent_change >= CHANGE_TRIGGER_B_HI and float(price) > float(avg_price):
                if _should_alert(head_key + "_HOD", now):
                    _send_heads_up(symbol, price, open_price, avg_price, percent_change, info, reason="שיא מקומי + מומנטום")

    except Exception as e:
        logging.error("WebSocket message error: %s", e)

def start_websocket(symbols_info: list[dict]):
    """הפעלת חיבור WebSocket לפין-האב עם ping ו-reconnect (backoff)."""
    def on_message_wrapper(ws, message):
        on_message(ws, message, symbols_info)

    backoff = 1

    def _open(ws):
        logging.info("🔗 WebSocket opened. Subscribing...")
        for sym in symbols_info:
            try:
                ws.send(json.dumps({"type": "subscribe", "symbol": sym["symbol"]}))
                time.sleep(0.05)  # האטה כדי למנוע חניקת שרות
            except Exception as e:
                logging.error("subscribe error for %s: %s", sym.get("symbol"), e)
        nonlocal backoff
        backoff = 1

    def _error(ws, err):
        logging.error("WebSocket error: %s", err)

    def _close(ws, *args):
        logging.warning("[INFO] WebSocket closed.")

    def _runner():
        nonlocal backoff
        while True:
            try:
                ws = WebSocketApp(
                    f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}",
                    on_message=on_message_wrapper,
                    on_open=_open,
                    on_error=_error,
                    on_close=_close
                )
                ws.run_forever(ping_interval=PING_INTERVAL, ping_timeout=PING_INTERVAL - 5)
            except Exception as e:
                logging.error("WebSocket crashed: %s", e)

            # backoff לפני נסיון התחברות מחדש
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)

    threading.Thread(target=_runner, daemon=True).start()
