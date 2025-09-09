# session_time.py
import datetime as dt
import pytz

NYSE_TZ = pytz.timezone("America/New_York")

def get_session_label(now_utc: dt.datetime | None = None) -> str:
    if now_utc is None:
        now_utc = dt.datetime.utcnow().replace(tzinfo=pytz.utc)
    now_et = now_utc.astimezone(NYSE_TZ)
    t = now_et.time()
    if dt.time(4, 0) <= t < dt.time(9, 30):
        return "pre"
    elif dt.time(9, 30) <= t < dt.time(16, 0):
        return "regular"
    elif dt.time(16, 0) <= t < dt.time(20, 0):
        return "post"
    return "closed"

def session_start_end(now_utc: dt.datetime | None = None) -> tuple[dt.datetime, dt.datetime]:
    if now_utc is None:
        now_utc = dt.datetime.utcnow().replace(tzinfo=pytz.utc)
    now_et = now_utc.astimezone(NYSE_TZ)
    d = now_et.date()
    pre_start   = NYSE_TZ.localize(dt.datetime.combine(d, dt.time(4, 0)))
    regular_start = NYSE_TZ.localize(dt.datetime.combine(d, dt.time(9, 30)))
    regular_end   = NYSE_TZ.localize(dt.datetime.combine(d, dt.time(16, 0)))
    post_end      = NYSE_TZ.localize(dt.datetime.combine(d, dt.time(20, 0)))
    # מחזירים חלון רלוונטי (from,to) לפי ה-session
    s = get_session_label(now_utc)
    if s == "pre":     return pre_start.astimezone(dt.timezone.utc), regular_start.astimezone(dt.timezone.utc)
    if s == "regular": return regular_start.astimezone(dt.timezone.utc), regular_end.astimezone(dt.timezone.utc)
    if s == "post":    return regular_end.astimezone(dt.timezone.utc), post_end.astimezone(dt.timezone.utc)
    # מחוץ לשעות – ברירת מחדל: היום 4:00→20:00
    return pre_start.astimezone(dt.timezone.utc), post_end.astimezone(dt.timezone.utc)
