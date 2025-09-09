# metrics_service.py
import time, logging
from datetime import datetime, timezone, timedelta
import requests
from session_time import session_start_end, get_session_label
from telegram_service import send_to_telegram
from news_service import get_today_news
from math import isfinite
from config import FINNHUB_API_KEY

REQUEST_TIMEOUT = 10

def _get_candles(symbol: str, resolution: str, ts_from: int, ts_to: int):
    url = (f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}"
           f"&resolution={resolution}&from={ts_from}&to={ts_to}&token={FINNHUB_API_KEY}")
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        return j if j.get("s") == "ok" else None
    except Exception as e:
        logging.error("candles fetch failed %s: %s", symbol, e)
        return None

def _fmt_money(x: float) -> str:
    try:
        if x >= 1_000_000_000: return f"${x/1_000_000_000:.2f}B"
        if x >= 1_000_000:     return f"${x/1_000_000:.2f}M"
        if x >= 1_000:         return f"${x/1_000:.2f}K"
        return f"${x:.0f}"
    except Exception:
        return "—"

def _vwap_from_candles(c: list[float], v: list[float]) -> float | None:
    try:
        num = sum(ci*vi for ci,vi in zip(c, v))
        den = sum(v)
        return num/den if den > 0 else None
    except Exception:
        return None

def _send(symbol, title_tag, body_lines: list[str]):
    now = datetime.now().strftime("%H:%M:%S")
    news = get_today_news(symbol)
    msg = (
        f"<b>📡 {title_tag}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📈 <b>{symbol}</b>\n"
        + "\n".join(body_lines) + "\n\n"
        f"{news}\n"
        f"🔗 <a href='https://www.tradingview.com/symbols/{symbol}/'>גרף חי</a>  •  ⏱️ {now}"
    )
    send_to_telegram(msg)

def start_metrics(symbols_info: list[dict], poll_sec: int = 30):
    """
    מריץ לולאה רקע לכל הסימולים: 1m candles מאז תחילת הסשן → VWAP/HOD/Volume Spike
    שולח התראות כאשר יש טריגר.
    """
    state = {}  # per-symbol state
    def loop():
        while True:
            try:
                session_from, session_to = session_start_end()
                f_ts = int(session_from.timestamp()); t_ts = int(datetime.now(timezone.utc).timestamp())
                session = get_session_label()
                for info in symbols_info:
                    sym = info["symbol"]
                    j = _get_candles(sym, "1", f_ts, t_ts)
                    if not j: continue
                    c, v, h = j.get("c",[]), j.get("v",[]), j.get("h",[])
                    if len(c) < 3: continue
                    last = c[-1]; prev = c[-2]
                    vol_last = v[-1]
                    # VWAP
                    vwap = _vwap_from_candles(c, v)
                    # avg 1m volume (20)
                    avg1 = sum(v[-21:-1]) / max(1, len(v[-21:-1])) if len(v) > 21 else (sum(v)/len(v) if v else 0)
                    # HOD
                    hod = max(h) if h else last
                    # שמירה והסקת טריגרים
                    st = state.setdefault(sym, {"prev_above_vwap": None, "last_hod": hod})
                    was_above = st["prev_above_vwap"]
                    is_above  = (vwap is not None and last > vwap)
                    # VWAP Reclaim
                    if vwap and was_above is False and is_above:
                        body = [
                            f"🟩 <b>VWAP Reclaim</b> ({session})",
                            f"💰 Price: <b>${last:.2f}</b>  |  VWAP: ${vwap:.2f}",
                            f"📦 1m Vol: {_fmt_money(vol_last)} (avg: {_fmt_money(avg1)})",
                        ]
                        _send(sym, "Heads-up", body)
                    st["prev_above_vwap"] = is_above if vwap is not None else was_above
                    # Volume Spike
                    if avg1 and vol_last >= 3.0 * avg1:
                        change_5m = ((last - c[-6]) / c[-6] * 100.0) if len(c) >= 6 and c[-6] else 0.0
                        body = [
                            f"📈 <b>Volume Spike</b> ×{vol_last/max(1,avg1):.2f} ({session})",
                            f"💰 Price: <b>${last:.2f}</b>  |  Δ5m: {change_5m:.2f}%",
                        ]
                        _send(sym, "Heads-up", body)
                    # HOD Breakout
                    prev_hod = st.get("last_hod", hod)
                    if isfinite(last) and last > prev_hod * 1.001:  # buffer 0.1%
                        body = [
                            f"🚀 <b>HOD Breakout</b> ({session})",
                            f"💰 Price: <b>${last:.2f}</b>  |  HOD: ${prev_hod:.2f}",
                        ]
                        _send(sym, "Heads-up", body)
                        st["last_hod"] = last
                    else:
                        st["last_hod"] = max(prev_hod, hod)
            except Exception as e:
                logging.error("metrics loop error: %s", e)
            time.sleep(poll_sec)
    import threading
    threading.Thread(target=loop, daemon=True).start()
