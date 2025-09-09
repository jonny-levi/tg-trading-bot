# stock_fetcher.py
# -*- coding: utf-8 -*-
import time
import requests
import logging
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import FINNHUB_API_KEY

# ===== קריטריונים קשיחים =====
MIN_PRICE_USD        = 0.30
MAX_PRICE_USD        = 15.00
MIN_INTRADAY_VOLUME  = 50_000            # כולל פרה-מרקט
MAX_MARKET_CAP_USD   = 1_500_000_000     # עד 1.5B
MIN_SHORT_FLOAT_PCT  = 10.0

# ===== ספים רכים לניקוד =====
MIN_SCORE            = 50                # Tier B מתחיל מ-50; A מ-70
RVOL_TARGETS         = (1.5, 2.5)        # 1.5x / 2.5x
GAP_TARGETS_PCT      = (1.0, 40.0)       # GapUp "סביר" לעבודה
ATR_TARGETS_PCT      = (4.0, 25.0)       # ATR% "בריא"
MIN_AVG_DOLLAR_VOL   = 500_000
GOOD_AVG_DOLLAR_VOL  = 1_000_000

# ===== עומסי עבודה ורשת =====
MAX_WORKERS_STAGE1   = 6
MAX_WORKERS_STAGE2   = 4
REQUEST_TIMEOUT      = 12

# ===== HTTP =====
def _safe_get_json(url, timeout=REQUEST_TIMEOUT):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 429:
            time.sleep(0.8)
            r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error("GET failed for %s: %s", url, e)
        return None

# ===== עזרי נתונים =====
def _get_quote(symbol: str):
    return _safe_get_json(f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}")

def _get_profile(symbol: str):
    return _safe_get_json(f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={FINNHUB_API_KEY}")

def _get_metric(symbol: str):
    return _safe_get_json(f"https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={FINNHUB_API_KEY}")

def _get_candles(symbol: str, resolution: str, ts_from: int, ts_to: int):
    url = (f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}"
           f"&resolution={resolution}&from={ts_from}&to={ts_to}&token={FINNHUB_API_KEY}")
    return _safe_get_json(url)

def _get_intraday_volume(symbol: str, minutes_back: int = 240) -> int:
    """נפח אינטרדיי מצטבר (כולל פרה-מרקט) ברזולוציית 5 דק'."""
    now = datetime.now(timezone.utc)
    _from = int((now - timedelta(minutes=minutes_back)).timestamp())
    _to   = int(now.timestamp())
    data = _get_candles(symbol, "5", _from, _to)
    if not data or data.get("s") != "ok":
        return 0
    vols = data.get("v") or []
    return int(sum(vols))

def _extract_short_float(metric_json: dict) -> float | None:
    """מחלץ Short Float% (0–100) מתוך metric – מנסה כמה שמות-שדה נפוצים."""
    if not metric_json:
        return None
    m = metric_json.get("metric") or {}
    candidates = [
        "shortPercentFloat", "ShortPercentFloat",
        "shortRatio", "ShortRatio",
        "ShortInterestFloat", "shortInterestFloat",
        "shortInterestPercentFloat", "ShortPercentOfFloat"
    ]
    for k in candidates:
        val = m.get(k)
        if val is None:
            continue
        try:
            val = float(val)
            if val <= 1.0:  # לפעמים מגיע ביחס (0–1)
                val *= 100.0
            return val
        except Exception:
            continue
    return None

def _atr_percent(symbol: str, days: int = 30) -> float | None:
    """ATR(14) כאחוז מהמחיר האחרון, על בסיס נרות יומיים."""
    now = datetime.now(timezone.utc)
    _from = int((now - timedelta(days=days+5)).timestamp())
    _to   = int(now.timestamp())
    data = _get_candles(symbol, "D", _from, _to)
    if not data or data.get("s") != "ok":
        return None
    o, h, l, c = data.get("o", []), data.get("h", []), data.get("l", []), data.get("c", [])
    n = min(len(o), len(h), len(l), len(c))
    if n < 15:
        return None

    trs = []
    for i in range(1, n):
        high = h[i]; low = l[i]; prev_close = c[i-1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    if len(trs) < 14:
        return None
    atr14 = sum(trs[-14:]) / 14.0
    last_c = c[-1]
    if not last_c or last_c <= 0:
        return None
    return (atr14 / last_c) * 100.0

def _avg_dollar_volume_10d(symbol: str) -> float | None:
    """ממוצע Dollar-Volume ל-10 ימים (נרות יומיים)."""
    now = datetime.now(timezone.utc)
    _from = int((now - timedelta(days=30)).timestamp())
    _to   = int(now.timestamp())
    data = _get_candles(symbol, "D", _from, _to)
    if not data or data.get("s") != "ok":
        return None
    c = data.get("c") or []
    v = data.get("v") or []
    n = min(len(c), len(v))
    if n < 10:
        return None
    last10_c = c[-10:]
    last10_v = v[-10:]
    dollar_vols = [float(cc) * float(vv) for cc, vv in zip(last10_c, last10_v)]
    return sum(dollar_vols) / len(dollar_vols)

# ===== ניקוד =====
def _score(entry: dict) -> int:
    """ניקוד 0–100 לפי איכות הסיגנל."""
    score = 0

    # Short float
    sf = entry.get("short_float") or 0.0
    if sf >= 10:
        score += 20
        if sf >= 20: score += 8

    # RVOL
    rvol = entry.get("rvol")
    if rvol is not None:
        if rvol >= RVOL_TARGETS[0]: score += 20
        if rvol >= RVOL_TARGETS[1]: score += 10

    # Gap%
    gap = entry.get("gap_pct")
    if gap is not None and GAP_TARGETS_PCT[0] <= gap <= GAP_TARGETS_PCT[1]:
        score += 20
        if 5.0 <= gap <= 20.0: score += 10

    # ATR%
    atrp = entry.get("atr_pct")
    if atrp is not None and ATR_TARGETS_PCT[0] <= atrp <= ATR_TARGETS_PCT[1]:
        score += 15

    # Avg$Vol
    adv = entry.get("avg_dollar_vol_10d") or 0
    if adv >= MIN_AVG_DOLLAR_VOL: score += 10
    if adv >= GOOD_AVG_DOLLAR_VOL: score += 5

    # Momentum מול Open
    momentum = entry.get("momentum_from_open_pct")
    if momentum is not None and momentum >= 3.0:
        score += 10

    return min(score, 100)

# ===== שלבים =====
def _stage1_basic_filters(symbol: str) -> dict | None:
    """שלב 1 – בדיקות מהירות: MarketCap + מחיר (ציטוט) + Gap + Momentum."""
    profile = _get_profile(symbol)
    if not profile:
        return None
    mcap = profile.get("marketCapitalization") or 0
    if mcap <= 0 or mcap > MAX_MARKET_CAP_USD:
        return None

    quote = _get_quote(symbol)
    if not quote:
        return None

    c = quote.get("c"); o = quote.get("o"); pc = quote.get("pc")
    if c is None or o is None or pc is None:
        return None
    c = float(c); o = float(o); pc = float(pc)

    if c < MIN_PRICE_USD or c > MAX_PRICE_USD:
        return None

    momentum_from_open_pct = ((c - o) / o) * 100.0 if o > 0 else 0.0
    gap_pct = ((c - pc) / pc) * 100.0 if pc > 0 else None

    return {
        "symbol": symbol,
        "open": o,
        "price": c,
        "market_cap": float(mcap),
        "gap_pct": gap_pct,
        "momentum_from_open_pct": momentum_from_open_pct,
        "prev_close": pc,  # לשימוש SSR בהודעות WS
    }

def _stage2_deep_filters(entry: dict) -> dict | None:
    """שלב 2 – Short Float + Intraday Volume + RVOL + ATR% + Avg$Vol(10d) + ניקוד."""
    symbol = entry["symbol"]

    metric = _get_metric(symbol)
    short_float = _extract_short_float(metric)
    if short_float is None or short_float < MIN_SHORT_FLOAT_PCT:
        return None

    intraday_vol = _get_intraday_volume(symbol, minutes_back=240)
    if intraday_vol < MIN_INTRADAY_VOLUME:
        return None

    avg_daily_vol_10d_dollar = _avg_dollar_volume_10d(symbol)
    atr_pct = _atr_percent(symbol, days=30)

    # RVOL ביחידות מניה (מול ממוצע 10 ימים)
    now = datetime.now(timezone.utc)
    _from = int((now - timedelta(days=30)).timestamp())
    _to   = int(now.timestamp())
    ddata = _get_candles(symbol, "D", _from, _to)
    avg_vol_10d_units = None
    if ddata and ddata.get("s") == "ok":
        vols = ddata.get("v") or []
        if len(vols) >= 10:
            avg_vol_10d_units = sum(vols[-10:]) / 10.0

    if avg_vol_10d_units and avg_vol_10d_units > 0:
        rvol = intraday_vol / avg_vol_10d_units
    else:
        rvol = None

    entry.update({
        "short_float": short_float,
        "intraday_volume": int(intraday_vol),
        "avg_dollar_vol_10d": float(avg_daily_vol_10d_dollar) if avg_daily_vol_10d_dollar else None,
        "atr_pct": float(atr_pct) if atr_pct is not None else None,
        "rvol": float(rvol) if rvol is not None else None,
    })

    entry["score"] = _score(entry)
    if entry["score"] < MIN_SCORE:
        return None

    return entry

# ===== API ראשי =====
def get_microcap_symbols(limit=50, priority_symbols: list[str] | None = None):
    """
    מחזיר עד limit מניות US שעומדות בקריטריונים:
    Price ∈ [0.30, 15], MarketCap ≤ 1.5B, ShortFloat ≥ 10%, Intraday Volume ≥ 50k,
    + ניקוד איכות ≥ 50 (Tier B) או ≥ 70 (Tier A). ממויין לפי ציון יורד.
    priority_symbols (אופציונלי) – רשימת טיקרים לבדיקה מוקדמת (למשל מיוטיוב).
    """
    base = _safe_get_json(f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={FINNHUB_API_KEY}") or []
    logging.info("✅ Fetched %d US symbols.", len(base))

    # דילוג על Warrants/Units/Preferred
    universe = []
    for s in base:
        sym = s.get("symbol") or ""
        desc = (s.get("description") or "").upper()
        if not sym:
            continue
        if any(x in desc for x in ("WARRANT", "UNIT", "PREF", "PREFERRED")):
            continue
        universe.append(sym)

    # סדר עדיפות: קודם priority_symbols (אם נמסרו), אחר כך שאר היקום
    seen = set()
    ordered = []
    if priority_symbols:
        for s in priority_symbols:
            if s in universe and s not in seen:
                ordered.append(s); seen.add(s)
    for s in universe:
        if s not in seen:
            ordered.append(s)

    # שלב 1 – MarketCap + Price + Gap + Momentum
    stage1 = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_STAGE1) as ex:
        futs = {ex.submit(_stage1_basic_filters, sym): sym for sym in ordered}
        for f in as_completed(futs):
            try:
                res = f.result()
                if res:
                    stage1.append(res)
            except Exception as e:
                logging.error("Stage1 failed for %s: %s", futs[f], e)

    logging.info("Stage1 passed: %d", len(stage1))

    # שלב 2 – Short Float + Volume + RVOL + ATR% + Avg$Vol + Score
    selected = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_STAGE2) as ex:
        futs = {ex.submit(_stage2_deep_filters, row): row["symbol"] for row in stage1}
        for f in as_completed(futs):
            try:
                res = f.result()
                if res:
                    # שיוך שכבה
                    res["tier"] = "A" if res["score"] >= 70 else "B"
                    selected.append(res)
                    if len(selected) >= limit:
                        break
            except Exception as e:
                logging.error("Stage2 failed for %s: %s", futs[f], e)

    # מיון לפי ציון יורד
    selected.sort(key=lambda x: x.get("score", 0), reverse=True)
    logging.info("✅ Total selected: %d", len(selected))
    return selected[:limit]
